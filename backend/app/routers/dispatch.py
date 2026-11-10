from datetime import UTC, datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.authentication import require_roles
from app.models.assignment import Assignment, AssignmentStatus
from app.models.order import Order, OrderStatus
from app.models.rider_location import RiderLocation
from app.models.rider_profile import RiderAvailability, RiderProfile
from app.models.user import AccountStatus, User, UserRole
from app.schemas.dispatch import (
    AssignmentCreate,
    AssignmentReassign,
    AssignmentResponse,
    OrderReviewRequest,
    ReturnOrderRequest,
    RiderCandidateResponse,
)
from app.schemas.order import OrderResponse
from app.services.order_service import transition_order

router = APIRouter(
    prefix="/api/v1/dispatch",
    tags=["dispatch"],
    dependencies=[Depends(require_roles(UserRole.DISPATCHER))],
)
ACTIVE_ASSIGNMENTS = {AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED}


def _assignment_or_404(db: Session, assignment_id: int) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _available_rider(db: Session, rider_id: int) -> RiderProfile:
    rider = db.scalar(
        select(RiderProfile)
        .join(User)
        .where(
            RiderProfile.id == rider_id,
            RiderProfile.availability_status == RiderAvailability.AVAILABLE,
            User.account_status == AccountStatus.ACTIVE,
        )
    )
    if rider is None:
        raise HTTPException(status_code=409, detail="Rider is not available")
    active_assignment = db.scalar(
        select(Assignment.id).where(
            Assignment.rider_id == rider.id,
            Assignment.assignment_status.in_(ACTIVE_ASSIGNMENTS),
        )
    )
    if active_assignment is not None:
        raise HTTPException(status_code=409, detail="Rider already has an active assignment")
    return rider


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    value = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(
        d_lon / 2
    ) ** 2
    return 2 * earth_radius_km * asin(sqrt(value))


@router.get("/orders", response_model=list[OrderResponse])
def list_dispatch_orders(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.DISPATCHER)),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .where(Order.current_status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]))
            .order_by(Order.created_at)
            .limit(limit)
            .offset(offset)
        ).all()
    )


@router.patch("/orders/{order_id}/review", response_model=OrderResponse)
def review_order(
    order_id: int,
    payload: OrderReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.DISPATCHER)),
) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.current_status != OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="Only pending orders can be reviewed")
    next_status = (
        OrderStatus.CONFIRMED
        if payload.decision == "confirm"
        else OrderStatus.REJECTED
    )
    transition_order(db, order, next_status, user, payload.remarks)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/orders/{order_id}/return", response_model=OrderResponse)
def return_failed_order(
    order_id: int,
    payload: ReturnOrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.DISPATCHER)),
) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.current_status != OrderStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed orders can be returned")
    transition_order(db, order, OrderStatus.RETURNED, user, payload.remarks)
    db.commit()
    db.refresh(order)
    return order


@router.get("/riders", response_model=list[RiderCandidateResponse])
def list_available_riders(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.DISPATCHER)),
    pickup_latitude: float | None = Query(default=None, ge=-90, le=90),
    pickup_longitude: float | None = Query(default=None, ge=-180, le=180),
    max_distance_km: float = Query(default=50, gt=0, le=500),
) -> list[RiderCandidateResponse]:
    if (pickup_latitude is None) != (pickup_longitude is None):
        raise HTTPException(status_code=422, detail="Provide both pickup coordinates")
    candidates = db.scalars(
        select(RiderProfile)
        .join(User)
        .where(
            RiderProfile.availability_status == RiderAvailability.AVAILABLE,
            User.account_status == AccountStatus.ACTIVE,
        )
        .order_by(RiderProfile.id)
    ).all()
    results: list[RiderCandidateResponse] = []
    for rider in candidates:
        active_count = db.scalar(
            select(func.count(Assignment.id)).where(
                Assignment.rider_id == rider.id,
                Assignment.assignment_status.in_(ACTIVE_ASSIGNMENTS),
            )
        ) or 0
        if active_count:
            continue
        latest_location = db.scalar(
            select(RiderLocation)
            .where(RiderLocation.rider_id == rider.id)
            .order_by(RiderLocation.recorded_at.desc())
            .limit(1)
        )
        if latest_location is not None:
            recorded_at = latest_location.recorded_at
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.replace(tzinfo=UTC)
            if recorded_at < datetime.now(UTC) - timedelta(minutes=10):
                latest_location = None
        distance = None
        if latest_location is not None and pickup_latitude is not None:
            distance = _distance_km(
                pickup_latitude,
                pickup_longitude,
                latest_location.latitude,
                latest_location.longitude,
            )
            if distance > max_distance_km:
                continue
        results.append(
            RiderCandidateResponse(
                rider_id=rider.id,
                user_id=rider.user_id,
                full_name=rider.user.full_name,
                vehicle_type=rider.vehicle_type,
                vehicle_registration=rider.vehicle_registration,
                availability_status=rider.availability_status,
                active_assignments=active_count,
                distance_km=round(distance, 2) if distance is not None else None,
            )
        )
    return results


@router.post(
    "/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_rider(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.DISPATCHER)),
) -> Assignment:
    order = db.scalar(
        select(Order).where(Order.id == payload.order_id).with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.current_status != OrderStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only confirmed orders can be assigned")
    rider = _available_rider(db, payload.rider_id)
    assignment = Assignment(
        order_id=order.id,
        rider_id=rider.id,
        dispatcher_id=user.id,
        assignment_status=AssignmentStatus.PENDING,
    )
    db.add(assignment)
    transition_order(
        db, order, OrderStatus.ASSIGNED, user, f"Assigned to rider profile {rider.id}"
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Order or rider already has an active assignment"
        ) from None
    db.refresh(assignment)
    return assignment


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
def reassign_rider(
    assignment_id: int,
    payload: AssignmentReassign,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.DISPATCHER)),
) -> Assignment:
    assignment = db.scalar(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .with_for_update()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.assignment_status not in ACTIVE_ASSIGNMENTS | {AssignmentStatus.WITHDRAWN}:
        raise HTTPException(status_code=409, detail="This assignment cannot be reassigned")
    if assignment.rider_id == payload.rider_id:
        raise HTTPException(status_code=422, detail="Choose a different rider")
    order = db.scalar(select(Order).where(Order.id == assignment.order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if (
        assignment.assignment_status == AssignmentStatus.WITHDRAWN
        and order.current_status != OrderStatus.FAILED
    ):
        raise HTTPException(status_code=409, detail="Only failed deliveries can restart a withdrawn assignment")
    new_rider = _available_rider(db, payload.rider_id)

    old_rider_id = assignment.rider_id
    assignment.assignment_status = AssignmentStatus.WITHDRAWN
    if order.current_status == OrderStatus.ACCEPTED:
        transition_order(
            db, order, OrderStatus.CONFIRMED, user, "Assignment withdrawn for reassignment"
        )
        transition_order(
            db,
            order,
            OrderStatus.ASSIGNED,
            user,
            f"Reassigned to rider profile {new_rider.id}",
        )
    elif order.current_status == OrderStatus.FAILED:
        transition_order(
            db, order, OrderStatus.ASSIGNED, user, f"Reassigned to rider profile {new_rider.id}"
        )
    elif order.current_status != OrderStatus.ASSIGNED:
        raise HTTPException(status_code=409, detail="Order is not in a reassignable state")

    replacement = Assignment(
        order_id=order.id,
        rider_id=new_rider.id,
        dispatcher_id=user.id,
        assignment_status=AssignmentStatus.PENDING,
    )
    db.add(replacement)
    old_rider = db.get(RiderProfile, old_rider_id)
    if old_rider is not None and old_rider.availability_status == RiderAvailability.ON_DELIVERY:
        old_rider.availability_status = RiderAvailability.AVAILABLE
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Order or rider already has an active assignment"
        ) from None
    db.refresh(replacement)
    return replacement