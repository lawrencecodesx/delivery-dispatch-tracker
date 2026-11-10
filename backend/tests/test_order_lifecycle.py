from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.order import OrderStatus
from app.schemas.user import UserCreate
from app.services.order_service import ALLOWED_STATUS_TRANSITIONS, transition_order
from app.services.pricing import calculate_delivery_fee


class RecordingSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, instance: object) -> None:
        self.added.append(instance)


def test_status_lifecycle_matches_project_plan() -> None:
    assert ALLOWED_STATUS_TRANSITIONS == {
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


def test_valid_transition_records_actor_and_previous_status() -> None:
    db = RecordingSession()
    order = SimpleNamespace(id=12, current_status=OrderStatus.PENDING)
    actor = SimpleNamespace(id=7)

    transition_order(db, order, OrderStatus.CONFIRMED, actor, "Reviewed")

    assert order.current_status == OrderStatus.CONFIRMED
    assert len(db.added) == 1
    event = db.added[0]
    assert event.order_id == 12
    assert event.updated_by == 7
    assert event.previous_status == OrderStatus.PENDING
    assert event.new_status == OrderStatus.CONFIRMED
    assert event.remarks == "Reviewed"


def test_invalid_transition_is_rejected_without_mutating_order() -> None:
    db = RecordingSession()
    order = SimpleNamespace(id=12, current_status=OrderStatus.DELIVERED)
    actor = SimpleNamespace(id=7)

    with pytest.raises(HTTPException) as error:
        transition_order(db, order, OrderStatus.PENDING, actor)

    assert error.value.status_code == 409
    assert order.current_status == OrderStatus.DELIVERED
    assert db.added == []


def test_registration_schema_normalizes_submitted_role() -> None:
    user = UserCreate.model_validate({
        "email": "customer@example.com",
        "password": "long-enough-password",
        "role": "CUSTOMER",
    })

    assert user.role.value == "customer"


def test_delivery_fee_uses_straight_line_distance_and_cent_rounding() -> None:
    fee = calculate_delivery_fee(5.6, -0.18, 5.6, -0.18)
    assert str(fee) == "5.00"

    longer_route = calculate_delivery_fee(5.6, -0.18, 5.61, -0.19)
    assert longer_route > fee
    assert len(str(longer_route).split(".")[1]) == 2
