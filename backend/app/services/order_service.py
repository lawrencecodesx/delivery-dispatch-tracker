from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.order_history import OrderStatusHistory
from app.models.user import User

ALLOWED_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.CONFIRMED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.CONFIRMED: {OrderStatus.ASSIGNED, OrderStatus.CANCELLED},
    OrderStatus.ASSIGNED: {OrderStatus.ACCEPTED, OrderStatus.CONFIRMED},
    OrderStatus.ACCEPTED: {OrderStatus.PICKED_UP, OrderStatus.CONFIRMED},
    OrderStatus.PICKED_UP: {OrderStatus.IN_TRANSIT},
    OrderStatus.IN_TRANSIT: {OrderStatus.DELIVERED, OrderStatus.FAILED},
    OrderStatus.FAILED: {OrderStatus.ASSIGNED, OrderStatus.RETURNED},
    OrderStatus.REJECTED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.DELIVERED: set(),
    OrderStatus.RETURNED: set(),
}


def transition_order(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    actor: User,
    remarks: str | None = None,
) -> None:
    previous_status = order.current_status
    if new_status not in ALLOWED_STATUS_TRANSITIONS[previous_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order cannot transition from {previous_status.value} to {new_status.value}",
        )
    order.current_status = new_status
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            updated_by=actor.id,
            previous_status=previous_status,
            new_status=new_status,
            remarks=remarks,
        )
    )