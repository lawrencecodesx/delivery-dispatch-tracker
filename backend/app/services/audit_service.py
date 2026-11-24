import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.order_history import OrderStatusHistory

GENESIS_HASH = "0" * 64


def _status_value(status: OrderStatus | None) -> str | None:
    return status.value if status is not None else None


def _record_hash(
    *,
    order_id: int,
    sequence_num: int,
    old_status: OrderStatus | None,
    new_status: OrderStatus,
    actor_id: int,
    timestamp: datetime,
    prev_hash: str,
) -> str:
    timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp
    data = {
        "order_id": order_id,
        "sequence_num": sequence_num,
        "old_status": _status_value(old_status),
        "new_status": _status_value(new_status),
        "actor_id": actor_id,
        "timestamp_iso": timestamp.astimezone(UTC).isoformat(),
        "prev_hash": prev_hash,
    }
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def append_status_history(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
    old_status: OrderStatus | None,
    new_status: OrderStatus,
    remarks: str | None = None,
    timestamp: datetime | None = None,
) -> OrderStatusHistory:
    db.scalar(select(Order.id).where(Order.id == order_id).with_for_update())
    previous = db.scalar(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.sequence_num.desc())
        .limit(1)
        .with_for_update()
    )
    sequence_num = previous.sequence_num + 1 if previous else 1
    prev_hash = previous.record_hash if previous else GENESIS_HASH
    updated_at = timestamp or datetime.now(UTC)
    record = OrderStatusHistory(
        order_id=order_id,
        updated_by=actor_id,
        previous_status=old_status,
        new_status=new_status,
        remarks=remarks,
        updated_at=updated_at,
        sequence_num=sequence_num,
        prev_hash=prev_hash,
        record_hash=_record_hash(
            order_id=order_id,
            sequence_num=sequence_num,
            old_status=old_status,
            new_status=new_status,
            actor_id=actor_id,
            timestamp=updated_at,
            prev_hash=prev_hash,
        ),
    )
    db.add(record)
    db.flush()
    return record


def append_audit_event(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
    status: OrderStatus,
    event: str,
) -> OrderStatusHistory:
    return append_status_history(
        db,
        order_id=order_id,
        actor_id=actor_id,
        old_status=status,
        new_status=status,
        remarks=event,
    )


def verify_status_history(records: list[OrderStatusHistory]) -> dict[str, int | bool | None]:
    previous_hash = GENESIS_HASH
    verified = 0
    for expected_sequence, record in enumerate(records, start=1):
        if record.sequence_num != expected_sequence or record.prev_hash != previous_hash:
            return {
                "is_valid": False,
                "verified_records": verified,
                "broken_at_sequence": record.sequence_num,
            }
        expected_hash = _record_hash(
            order_id=record.order_id,
            sequence_num=record.sequence_num,
            old_status=record.previous_status,
            new_status=record.new_status,
            actor_id=record.updated_by,
            timestamp=record.updated_at,
            prev_hash=record.prev_hash,
        )
        if record.record_hash != expected_hash:
            return {
                "is_valid": False,
                "verified_records": verified,
                "broken_at_sequence": record.sequence_num,
            }
        previous_hash = record.record_hash
        verified += 1
    return {
        "is_valid": True,
        "verified_records": verified,
        "broken_at_sequence": None,
    }
