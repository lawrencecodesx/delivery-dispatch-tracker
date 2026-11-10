from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, verify_password
from app.database.connection import get_db
from app.dependencies.authentication import require_roles
from app.models.assignment import Assignment, AssignmentStatus
from app.models.delivery_proof import DeliveryProof
from app.models.notification import Notification
from app.models.order import Order, OrderStatus
from app.models.rider_location import RiderLocation
from app.models.rider_profile import RiderAvailability, RiderProfile
from app.models.user import User, UserRole
from app.schemas.notification import DeliveryProofResponse
from app.schemas.rider import (
    AssignmentDecision,
    AssignmentResponse,
    AvailabilityUpdate,
    DeliveryProofCreate,
    RiderLocationCreate,
    RiderLocationResponse,
    RiderStatusUpdate,
)
from app.services.order_service import transition_order

router = APIRouter(
    prefix="/api/v1/rider",
    tags=["rider"],
    dependencies=[Depends(require_roles(UserRole.RIDER))],
)
ACTIVE_ASSIGNMENTS = {AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED}


def _rider_profile(db: Session, user: User) -> RiderProfile:
    profile = db.scalar(select(RiderProfile).where(RiderProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=403, detail="No rider profile is configured")
    return profile


def _owned_assignment(
    db: Session, assignment_id: int, rider: RiderProfile
) -> Assignment:
    assignment = db.scalar(
        select(Assignment)
        .options(selectinload(Assignment.order))
        .where(Assignment.id == assignment_id, Assignment.rider_id == rider.id)
        .with_for_update()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _active_assignment_for_order(
    db: Session, order_id: int, rider: RiderProfile
) -> Assignment:
    assignment = db.scalar(
        select(Assignment)
        .where(
            Assignment.order_id == order_id,
            Assignment.rider_id == rider.id,
            Assignment.assignment_status == AssignmentStatus.ACCEPTED,
        )
        .with_for_update()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Active assignment not found")
    return assignment


@router.get("/deliveries", response_model=list[AssignmentResponse])
def list_deliveries(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.RIDER)),
    include_history: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Assignment]:
    rider = _rider_profile(db, user)
    query = (
        select(Assignment)
        .options(selectinload(Assignment.order))
        .where(Assignment.rider_id == rider.id)
        .order_by(Assignment.assigned_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if not include_history:
        query = query.where(Assignment.assignment_status.in_(ACTIVE_ASSIGNMENTS))
    return list(db.scalars(query).all())


@router.patch("/assignments/{assignment_id}/respond", response_model=AssignmentResponse)
def respond_to_assignment(
    assignment_id: int,
    payload: AssignmentDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.RIDER)),
) -> Assignment:
    rider = _rider_profile(db, user)
    assignment = _owned_assignment(db, assignment_id, rider)
    if assignment.assignment_status != AssignmentStatus.PENDING:
        raise HTTPException(status_code=409, detail="This assignment has already been answered")
    order = assignment.order
    if order.current_status != OrderStatus.ASSIGNED:
        raise HTTPException(status_code=409, detail="Order is not awaiting rider acceptance")

    if payload.decision == "accept":
        assignment.assignment_status = AssignmentStatus.ACCEPTED
        assignment.accepted_at = datetime.now(UTC)
        rider.availability_status = RiderAvailability.ON_DELIVERY
        transition_order(
            db, order, OrderStatus.ACCEPTED, user, payload.remarks or "Rider accepted assignment"
        )
    else:
        assignment.assignment_status = AssignmentStatus.REJECTED
        rider.availability_status = RiderAvailability.AVAILABLE
        transition_order(
            db,
            order,
            OrderStatus.CONFIRMED,
            user,
            payload.remarks or "Rider declined assignment",
        )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.patch("/orders/{order_id}/status", response_model=OrderStatus)
def update_order_status(
    order_id: int,
    payload: RiderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.RIDER)),
) -> OrderStatus:
    rider = _rider_profile(db, user)
    assignment = _active_assignment_for_order(db, order_id, rider)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.status not in {OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT, OrderStatus.FAILED}:
        raise HTTPException(status_code=422, detail="Riders cannot set this order status")
    if payload.status == OrderStatus.IN_TRANSIT:
        issued_codes = db.scalar(
            select(func.count(DeliveryProof.id)).where(DeliveryProof.order_id == order.id)
        )
        failed_attempts = db.scalar(
            select(func.coalesce(func.sum(DeliveryProof.verification_attempts), 0)).where(
                DeliveryProof.order_id == order.id
            )
        )
        if issued_codes >= 3 or failed_attempts >= 5:
            raise HTTPException(
                status_code=429,
                detail="Delivery verification limit reached for this order",
            )
    transition_order(db, order, payload.status, user, payload.remarks)
    if payload.status == OrderStatus.IN_TRANSIT:
        db.add(
            Notification(
                user_id=order.customer_id,
                title="Delivery verification is ready",
                message=(
                    "Your order is in transit. Open its tracking page to request a "
                    "short-lived delivery verification code."
                ),
            )
        )
    if payload.status == OrderStatus.FAILED:
        rider.availability_status = RiderAvailability.AVAILABLE
        assignment.assignment_status = AssignmentStatus.WITHDRAWN
    db.commit()
    return order.current_status


@router.patch("/availability")
def update_availability(
    payload: AvailabilityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.RIDER)),
) -> dict[str, str]:
    rider = _rider_profile(db, user)
    has_active_assignment = db.scalar(
        select(Assignment.id).where(
            Assignment.rider_id == rider.id,
            Assignment.assignment_status == AssignmentStatus.ACCEPTED,
        )
    )
    if has_active_assignment and payload.availability_status != RiderAvailability.ON_DELIVERY:
        raise HTTPException(
            status_code=409,
            detail="Availability cannot change while an accepted delivery is active",
        )
    if (
        not has_active_assignment
        and payload.availability_status == RiderAvailability.ON_DELIVERY
    ):
        raise HTTPException(
            status_code=409,
            detail="On-delivery availability is managed by active assignments",
        )
    rider.availability_status = payload.availability_status
    db.commit()
    return {"availability_status": rider.availability_status.value}


@router.post(
    "/orders/{order_id}/proof",
    response_model=DeliveryProofResponse,
    status_code=status.HTTP_200_OK,
)
def submit_delivery_proof(
    order_id: int,
    payload: DeliveryProofCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.RIDER)),
) -> DeliveryProof:
    rider = _rider_profile(db, user)
    assignment = _active_assignment_for_order(db, order_id, rider)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None or order.current_status != OrderStatus.IN_TRANSIT:
        raise HTTPException(status_code=409, detail="Order is not awaiting delivery verification")
    proof = db.scalar(
        select(DeliveryProof)
        .where(
            DeliveryProof.order_id == order.id,
            DeliveryProof.verified_at.is_(None),
        )
        .order_by(DeliveryProof.created_at.desc(), DeliveryProof.id.desc())
        .limit(1)
        .with_for_update()
    )
    if proof is None:
        raise HTTPException(status_code=409, detail="No active verification code exists")
    failed_attempts = db.scalar(
        select(func.coalesce(func.sum(DeliveryProof.verification_attempts), 0)).where(
            DeliveryProof.order_id == order_id
        )
    )
    if failed_attempts >= 5:
        raise HTTPException(status_code=429, detail="Verification attempt limit reached")
    now = datetime.now(UTC)
    expiry = proof.code_expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if expiry <= now:
        raise HTTPException(status_code=409, detail="Verification code has expired")
    if not verify_password(payload.verification_code, proof.verification_code_hash):
        proof.verification_attempts += 1
        db.commit()
        if failed_attempts + 1 >= 5:
            raise HTTPException(status_code=429, detail="Verification attempt limit reached")
        raise HTTPException(status_code=400, detail="Invalid verification code")

    proof.image_url = str(payload.image_url)
    proof.verified_at = now
    transition_order(db, order, OrderStatus.DELIVERED, user, "Recipient code verified")
    assignment.assignment_status = AssignmentStatus.COMPLETED
    rider.availability_status = RiderAvailability.AVAILABLE
    db.commit()
    db.refresh(proof)
    return proof


@router.post("/location", response_model=RiderLocationResponse, status_code=201)
def update_location(
    payload: RiderLocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.RIDER)),
) -> RiderLocation:
    rider = _rider_profile(db, user)
    assignment = _active_assignment_for_order(db, payload.order_id, rider)
    order = db.get(Order, payload.order_id)
    if order is None or order.current_status not in {
        OrderStatus.ACCEPTED,
        OrderStatus.PICKED_UP,
        OrderStatus.IN_TRANSIT,
    }:
        raise HTTPException(status_code=409, detail="Location updates require an active delivery")
    recorded_at = payload.recorded_at or datetime.now(UTC)
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if recorded_at > now + timedelta(minutes=5) or recorded_at < now - timedelta(minutes=10):
        raise HTTPException(status_code=422, detail="Location timestamp is outside the allowed window")
    latest = db.scalar(
        select(RiderLocation)
        .where(RiderLocation.assignment_id == assignment.id)
        .order_by(RiderLocation.recorded_at.desc())
        .limit(1)
    )
    if latest is not None:
        latest_recorded_at = latest.recorded_at
        if latest_recorded_at.tzinfo is None:
            latest_recorded_at = latest_recorded_at.replace(tzinfo=UTC)
        if recorded_at <= latest_recorded_at:
            raise HTTPException(status_code=409, detail="Location timestamp must be newer")
        if recorded_at - latest_recorded_at < timedelta(seconds=5):
            raise HTTPException(
                status_code=429,
                detail="Location updates must be at least five seconds apart",
            )
    location = RiderLocation(
        rider_id=rider.id,
        assignment_id=assignment.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        recorded_at=recorded_at,
        accuracy=payload.accuracy,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location