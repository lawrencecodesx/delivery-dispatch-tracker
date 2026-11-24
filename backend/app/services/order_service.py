from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.audit_service import append_audit_event, append_status_history

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
    now = datetime.now(UTC)
    append_status_history(
        db,
        order_id=order.id,
        actor_id=actor.id,
        old_status=previous_status,
        new_status=new_status,
        remarks=remarks,
        timestamp=now,
    )
    deadline = getattr(order, "sla_deadline", None)
    if new_status == OrderStatus.DELIVERED and deadline is not None:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        if now > deadline and not order.sla_breached:
            effective_fee = order.split_fee_ghs
            if effective_fee is None:
                effective_fee = float(order.delivery_fee)
            order.sla_breached = True
            order.rebate_credited_ghs = round(float(effective_fee) * 0.25, 2)
            append_audit_event(
                db,
                order_id=order.id,
                actor_id=actor.id,
                status=new_status,
                event="SLA_BREACH_REBATE_ISSUED",
            )