import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.connection import get_db
from app.dependencies.authentication import get_current_user, require_roles
from app.models.assignment import Assignment, AssignmentStatus
from app.models.delivery_proof import DeliveryProof
from app.models.order import Order, OrderStatus
from app.models.order_history import OrderStatusHistory
from app.models.review import Review
from app.models.rider_profile import RiderProfile
from app.models.user import User, UserRole
from app.schemas.order import (
    CancelOrderRequest,
    DeliveryCodeResponse,
    OrderCreate,
    OrderDetailResponse,
    OrderResponse,
    OrderStatusHistoryResponse,
    PublicTrackingResponse,
    ReviewCreate,
    ReviewResponse,
)
from app.services.order_service import transition_order
from app.services.pricing import calculate_delivery_fee

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def _order_or_404(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _owned_or_operational_order(db: Session, order_id: int, user: User) -> Order:
    order = _order_or_404(db, order_id)
    if user.role in {UserRole.ADMIN, UserRole.DISPATCHER}:
        return order
    if user.role == UserRole.CUSTOMER:
        if order.customer_id != user.id:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    if user.role == UserRole.RIDER:
        profile = db.scalar(select(RiderProfile).where(RiderProfile.user_id == user.id))
        assigned = profile is not None and db.scalar(
            select(Assignment.id).where(
                Assignment.order_id == order.id,
                Assignment.rider_id == profile.id,
            )
        ) is not None
        if assigned:
            return order
    raise HTTPException(status_code=404, detail="Order not found")


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> Order:
    tracking_number = secrets.token_hex(16).upper()
    while db.scalar(select(Order.id).where(Order.tracking_number == tracking_number)):
        tracking_number = secrets.token_hex(16).upper()

    order = Order(
        customer_id=user.id,
        tracking_number=tracking_number,
        **payload.model_dump(),
        delivery_fee=calculate_delivery_fee(
            payload.pickup_latitude,
            payload.pickup_longitude,
            payload.destination_latitude,
            payload.destination_longitude,
        ),
    )
    db.add(order)
    db.flush()
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            updated_by=user.id,
            previous_status=None,
            new_status=OrderStatus.PENDING,
            remarks="Order created",
        )
    )
    db.commit()
    db.refresh(order)
    return order


@router.post(
    "/{order_id}/delivery-code",
    response_model=DeliveryCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_delivery_code(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> DeliveryCodeResponse:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.current_status != OrderStatus.IN_TRANSIT:
        raise HTTPException(
            status_code=409, detail="A delivery code is only available while in transit"
        )

    failed_attempts = db.scalar(
        select(func.coalesce(func.sum(DeliveryProof.verification_attempts), 0)).where(
            DeliveryProof.order_id == order.id
        )
    )
    if failed_attempts >= 5:
        raise HTTPException(status_code=429, detail="Verification attempt limit reached")

    issuance_count = db.scalar(
        select(func.count(DeliveryProof.id)).where(DeliveryProof.order_id == order.id)
    )
    if issuance_count >= 3:
        raise HTTPException(status_code=429, detail="Delivery code request limit reached")

    now = datetime.now(UTC)
    previous_proofs = db.scalars(
        select(DeliveryProof)
        .where(DeliveryProof.order_id == order.id, DeliveryProof.verified_at.is_(None))
        .with_for_update()
    ).all()
    for previous_proof in previous_proofs:
        previous_proof.code_expires_at = now

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = now + timedelta(minutes=15)
    db.add(
        DeliveryProof(
            order_id=order.id,
            verification_code_hash=hash_password(code),
            code_expires_at=expires_at,
        )
    )
    db.commit()
    return DeliveryCodeResponse(verification_code=code, expires_at=expires_at)


@router.get("", response_model=list[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    query = select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
    if user.role == UserRole.CUSTOMER:
        query = query.where(Order.customer_id == user.id)
    elif user.role == UserRole.RIDER:
        profile = db.scalar(select(RiderProfile).where(RiderProfile.user_id == user.id))
        if profile is None:
            return []
        query = query.join(Assignment).where(
            Assignment.rider_id == profile.id,
            Assignment.assignment_status.in_(
                [AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED]
            ),
        )
    return list(db.scalars(query).unique().all())


@router.get("/track/{tracking_number}", response_model=PublicTrackingResponse)
def public_tracking(tracking_number: str, db: Session = Depends(get_db)) -> PublicTrackingResponse:
    order = db.scalar(select(Order).where(Order.tracking_number == tracking_number.upper()))
    if order is None:
        raise HTTPException(status_code=404, detail="Tracking number not found")
    latest = db.scalar(
        select(OrderStatusHistory.updated_at)
        .where(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.updated_at.desc())
        .limit(1)
    )
    return PublicTrackingResponse(
        tracking_number=order.tracking_number,
        current_status=order.current_status,
        created_at=order.created_at,
        pickup_address=order.pickup_address,
        destination_address=order.destination_address,
        updated_at=latest,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderDetailResponse:
    order = _owned_or_operational_order(db, order_id, user)
    histories = list(
        db.scalars(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order.id)
            .order_by(OrderStatusHistory.updated_at)
        ).all()
    )
    return OrderDetailResponse(
        **OrderResponse.model_validate(order).model_dump(),
        status_history=[
            OrderStatusHistoryResponse.model_validate(entry) for entry in histories
        ],
    )


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    payload: CancelOrderRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Order:
    order = _order_or_404(db, order_id)
    if user.role == UserRole.CUSTOMER and order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role not in {UserRole.CUSTOMER, UserRole.DISPATCHER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only the customer or dispatch can cancel")
    if order.current_status not in {OrderStatus.PENDING, OrderStatus.CONFIRMED}:
        raise HTTPException(status_code=409, detail="This order can no longer be cancelled")
    transition_order(
        db, order, OrderStatus.CANCELLED, user, payload.remarks if payload else None
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/review", response_model=ReviewResponse, status_code=201)
def create_review(
    order_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> Review:
    order = _order_or_404(db, order_id)
    if order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.current_status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=409, detail="Only delivered orders can be reviewed")
    assignment = db.scalar(
        select(Assignment)
        .where(
            Assignment.order_id == order.id,
            Assignment.assignment_status == AssignmentStatus.COMPLETED,
        )
        .order_by(Assignment.assigned_at.desc())
    )
    if assignment is None:
        raise HTTPException(status_code=409, detail="The delivered order has no completed rider")
    review = Review(
        order_id=order.id,
        customer_id=user.id,
        rider_id=assignment.rider_id,
        **payload.model_dump(),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review