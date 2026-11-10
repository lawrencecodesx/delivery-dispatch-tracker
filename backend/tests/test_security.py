import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.database.base import Base
from app.database.connection import get_db
from app.main import app
from app.models import (
    Assignment,
    AssignmentStatus,
    DeliveryProof,
    Notification,
    Order,
    OrderStatus,
    RiderAvailability,
    RiderLocation,
    RiderProfile,
    User,
    UserRole,
)
from app.services.pricing import calculate_delivery_fee
from app.schemas.user import UserCreate

TEST_SECRET = "security-suite-secret-value-with-32-plus-characters"


@pytest.fixture
def security_context(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        with test_session() as session:
            yield session

    monkeypatch.setattr(settings, "JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ROLE_REGISTRATION", False)
    app.dependency_overrides[get_db] = override_db
    with test_session() as db:
        customer = User(
            email="owner@example.com",
            hashed_password=hash_password("owner-password-123"),
            role=UserRole.CUSTOMER,
        )
        other_customer = User(
            email="other@example.com",
            hashed_password=hash_password("other-password-123"),
            role=UserRole.CUSTOMER,
        )
        dispatcher = User(
            email="dispatch@example.com",
            hashed_password=hash_password("dispatch-password-123"),
            role=UserRole.DISPATCHER,
        )
        rider_user = User(
            email="rider@example.com",
            hashed_password=hash_password("rider-password-123"),
            role=UserRole.RIDER,
        )
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("admin-password-123"),
            role=UserRole.ADMIN,
        )
        other_rider_user = User(
            email="other-rider@example.com",
            hashed_password=hash_password("other-rider-password-123"),
            role=UserRole.RIDER,
        )
        db.add_all(
            [customer, other_customer, dispatcher, rider_user, other_rider_user, admin]
        )
        db.flush()
        rider = RiderProfile(
            user_id=rider_user.id,
            vehicle_type="bike",
            vehicle_registration="RID-001",
            availability_status=RiderAvailability.ON_DELIVERY,
        )
        other_rider = RiderProfile(
            user_id=other_rider_user.id,
            vehicle_type="bike",
            vehicle_registration="RID-002",
            availability_status=RiderAvailability.ON_DELIVERY,
        )
        db.add_all([rider, other_rider])
        db.flush()
        owned_order = Order(
            customer_id=customer.id,
            tracking_number="OWNED-TRACKING-0001",
            pickup_address="Pickup",
            pickup_latitude=5.6,
            pickup_longitude=-0.18,
            destination_address="Destination",
            destination_latitude=5.61,
            destination_longitude=-0.19,
            recipient_name="Recipient",
            recipient_phone="123456789",
            package_description="Parcel",
            delivery_fee=10,
            current_status=OrderStatus.IN_TRANSIT,
        )
        other_order = Order(
            customer_id=other_customer.id,
            tracking_number="OTHER-TRACKING-0002",
            pickup_address="Other pickup",
            pickup_latitude=5.6,
            pickup_longitude=-0.18,
            destination_address="Other destination",
            destination_latitude=5.61,
            destination_longitude=-0.19,
            recipient_name="Other recipient",
            recipient_phone="123456789",
            package_description="Other parcel",
            delivery_fee=10,
            current_status=OrderStatus.ACCEPTED,
        )
        historical_order = Order(
            customer_id=customer.id,
            tracking_number="HISTORICAL-TRACKING-0003",
            pickup_address="Historical pickup",
            pickup_latitude=5.6,
            pickup_longitude=-0.18,
            destination_address="Historical destination",
            destination_latitude=5.61,
            destination_longitude=-0.19,
            recipient_name="Historical recipient",
            recipient_phone="123456789",
            package_description="Historical parcel",
            delivery_fee=10,
            current_status=OrderStatus.DELIVERED,
        )
        db.add_all([owned_order, other_order, historical_order])
        db.flush()
        owned_assignment = Assignment(
            order_id=owned_order.id,
            rider_id=rider.id,
            dispatcher_id=dispatcher.id,
            assignment_status=AssignmentStatus.ACCEPTED,
            accepted_at=datetime.now(UTC),
        )
        historical_assignment = Assignment(
            order_id=historical_order.id,
            rider_id=rider.id,
            dispatcher_id=dispatcher.id,
            assignment_status=AssignmentStatus.COMPLETED,
            accepted_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db.add_all(
            [
                owned_assignment,
                historical_assignment,
                Assignment(
                    order_id=other_order.id,
                    rider_id=other_rider.id,
                    dispatcher_id=dispatcher.id,
                    assignment_status=AssignmentStatus.ACCEPTED,
                    accepted_at=datetime.now(UTC),
                ),
                DeliveryProof(
                    order_id=owned_order.id,
                    verification_code_hash=hash_password("123456"),
                    code_expires_at=datetime.now(UTC) + timedelta(minutes=15),
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                RiderLocation(
                    rider_id=rider.id,
                    assignment_id=owned_assignment.id,
                    latitude=5.6,
                    longitude=-0.18,
                    recorded_at=datetime.now(UTC),
                ),
                RiderLocation(
                    rider_id=rider.id,
                    assignment_id=historical_assignment.id,
                    latitude=9.0,
                    longitude=9.0,
                    recorded_at=datetime.now(UTC) - timedelta(minutes=30),
                ),
            ]
        )
        db.commit()
        tokens = {
            "customer": jwt.encode(
                {"sub": str(customer.id), "exp": datetime.now(UTC) + timedelta(minutes=30)},
                TEST_SECRET,
                algorithm="HS256",
            ),
            "other_customer": jwt.encode(
                {
                    "sub": str(other_customer.id),
                    "exp": datetime.now(UTC) + timedelta(minutes=30),
                },
                TEST_SECRET,
                algorithm="HS256",
            ),
            "dispatcher": jwt.encode(
                {
                    "sub": str(dispatcher.id),
                    "exp": datetime.now(UTC) + timedelta(minutes=30),
                },
                TEST_SECRET,
                algorithm="HS256",
            ),
            "rider": jwt.encode(
                {"sub": str(rider_user.id), "exp": datetime.now(UTC) + timedelta(minutes=30)},
                TEST_SECRET,
                algorithm="HS256",
            ),
            "admin": jwt.encode(
                {"sub": str(admin.id), "exp": datetime.now(UTC) + timedelta(minutes=30)},
                TEST_SECRET,
                algorithm="HS256",
            ),
        }
        ids = {
            "owned_order": owned_order.id,
            "other_order": other_order.id,
            "owned_rider": rider.id,
            "dispatcher_user": dispatcher.id,
            "customer_user": customer.id,
        }
    yield SimpleNamespace(
        request=_request,
        tokens=tokens,
        ids=ids,
        session_factory=test_session,
    )
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


async def _async_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict | None = None,
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, headers=headers, json=body)


def _request(method: str, path: str, *, token: str | None = None, body: dict | None = None):
    return asyncio.run(_async_request(method, path, token=token, body=body))


def test_cors_preflight_allows_configured_frontend_origin() -> None:
    async def preflight(origin: str) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )

    allowed = asyncio.run(preflight("http://localhost:5173"))
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"

    disallowed = asyncio.run(preflight("https://untrusted.example"))
    assert disallowed.status_code == 400
    assert "access-control-allow-origin" not in disallowed.headers


def test_public_registration_is_local_development_only(security_context, monkeypatch) -> None:
    customer = security_context.request(
        "POST",
        "/api/v1/auth/register",
        body={
            "full_name": "New Customer",
            "email": "new-customer@example.com",
            "password": "secure-password-123",
            "role": "CUSTOMER",
        },
    )
    assert customer.status_code == 201
    assert customer.json()["role"] == "customer"
    assert customer.json()["is_verified"] is True

    denied = security_context.request(
        "POST",
        "/api/v1/auth/register",
        body={
            "full_name": "Denied Dispatcher",
            "email": "denied-dispatcher@example.com",
            "password": "secure-password-123",
            "role": "DISPATCHER",
        },
    )
    assert denied.status_code == 403

    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ROLE_REGISTRATION", True)
    for role in ("DISPATCHER", "RIDER"):
        extra_fields = (
            {"vehicle_type": "Bicycle", "vehicle_registration": "TEST-001"}
            if role == "RIDER"
            else {}
        )
        response = security_context.request(
            "POST",
            "/api/v1/auth/register",
            body={
                "full_name": "New Operational User",
                "email": f"new-{role.lower()}@example.com",
                "password": "secure-password-123",
                "role": role,
                **extra_fields,
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == role.lower()
        assert response.json()["is_verified"] is False
        pending_login = security_context.request(
            "POST",
            "/api/v1/auth/login",
            body={
                "email": f"new-{role.lower()}@example.com",
                "password": "secure-password-123",
            },
        )
        assert pending_login.status_code == 403
        assert pending_login.json()["detail"] == "Account pending administrator approval."

        approved = security_context.request(
            "PATCH",
            f"/api/v1/users/{response.json()['id']}/approve",
            token=security_context.tokens["admin"],
        )
        assert approved.status_code == 200
        assert approved.json()["is_verified"] is True
        approved_login = security_context.request(
            "POST",
            "/api/v1/auth/login",
            body={
                "email": f"new-{role.lower()}@example.com",
                "password": "secure-password-123",
            },
        )
        assert approved_login.status_code == 200

    admin = security_context.request(
        "POST",
        "/api/v1/auth/register",
        body={
            "full_name": "Test Admin",
            "email": "test-admin@example.com",
            "password": "secure-password-123",
            "role": "ADMIN",
        },
    )
    assert admin.status_code == 403

    with security_context.session_factory() as db:
        rider = db.scalar(select(RiderProfile).where(RiderProfile.vehicle_registration == "TEST-001"))
        assert rider is not None
        assert rider.user.email == "new-rider@example.com"


def test_model_verification_defaults_are_role_aware(security_context) -> None:
    with security_context.session_factory() as db:
        customer = db.get(User, security_context.ids["customer_user"])
        dispatcher = db.get(User, security_context.ids["dispatcher_user"])
        rider = db.scalar(select(User).where(User.email == "rider@example.com"))
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))

    assert customer.is_verified is True
    assert dispatcher.is_verified is False
    assert rider.is_verified is False
    assert admin.is_verified is True


def test_public_role_registration_rejects_non_loopback_clients(
    security_context, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ROLE_REGISTRATION", True)

    async def remote_request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("198.51.100.10", 12345)),
            base_url="http://test",
        ) as client:
            return await client.post(
                "/api/v1/auth/register",
                headers={"Origin": "https://untrusted.example"},
                json={
                    "email": "remote-dispatcher@example.com",
                    "password": "secure-password-123",
                    "role": "DISPATCHER",
                },
            )

    assert asyncio.run(remote_request()).status_code == 403


def test_only_admins_can_approve_operational_accounts(security_context) -> None:
    forbidden = security_context.request(
        "PATCH",
        f"/api/v1/users/{security_context.ids['dispatcher_user']}/approve",
        token=security_context.tokens["customer"],
    )
    assert forbidden.status_code == 403


def test_approval_endpoint_rejects_customers(security_context) -> None:
    with security_context.session_factory() as db:
        customer_id = db.scalar(select(User.id).where(User.email == "owner@example.com"))

    response = security_context.request(
        "PATCH",
        f"/api/v1/users/{customer_id}/approve",
        token=security_context.tokens["admin"],
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only dispatcher and rider accounts require approval"


def test_admin_can_reject_pending_operational_accounts(security_context) -> None:
    response = security_context.request(
        "PATCH",
        f"/api/v1/users/{security_context.ids['dispatcher_user']}/reject",
        token=security_context.tokens["admin"],
    )

    assert response.status_code == 200
    assert response.json()["account_status"] == "suspended"
    assert response.json()["is_verified"] is False

    login = security_context.request(
        "POST",
        "/api/v1/auth/login",
        body={"email": "dispatch@example.com", "password": "dispatch-password-123"},
    )
    assert login.status_code == 403
    assert login.json()["detail"] == "This account is suspended"

    restored = security_context.request(
        "PATCH",
        f"/api/v1/users/{security_context.ids['dispatcher_user']}/approve",
        token=security_context.tokens["admin"],
    )
    assert restored.status_code == 200
    assert restored.json()["is_verified"] is True
    assert restored.json()["account_status"] == "active"

    login = security_context.request(
        "POST",
        "/api/v1/auth/login",
        body={"email": "dispatch@example.com", "password": "dispatch-password-123"},
    )
    assert login.status_code == 200


def test_only_admins_can_reject_pending_operational_accounts(security_context) -> None:
    response = security_context.request(
        "PATCH",
        f"/api/v1/users/{security_context.ids['dispatcher_user']}/reject",
        token=security_context.tokens["customer"],
    )

    assert response.status_code == 403


def test_rejection_endpoint_does_not_suspend_verified_users(security_context) -> None:
    response = security_context.request(
        "PATCH",
        f"/api/v1/users/{security_context.ids['customer_user']}/reject",
        token=security_context.tokens["admin"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only pending dispatcher and rider accounts can be rejected"


def test_local_forwarded_browser_can_register_role_when_origin_is_allowlisted(
    security_context, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ROLE_REGISTRATION", True)

    async def forwarded_request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("172.20.10.2", 12345)),
            base_url="http://localhost",
        ) as client:
            return await client.post(
                "/api/v1/auth/register",
                headers={"Origin": "http://127.0.0.1:5174"},
                json={
                    "email": "forwarded-dispatcher@example.com",
                    "password": "secure-password-123",
                    "role": "DISPATCHER",
                },
            )

    response = asyncio.run(forwarded_request())
    assert response.status_code == 201
    assert response.json()["role"] == "dispatcher"


def test_customers_cannot_read_or_cancel_other_customers_orders(security_context) -> None:
    token = security_context.tokens["other_customer"]
    order_id = security_context.ids["owned_order"]

    assert _request("GET", f"/api/v1/orders/{order_id}", token=token).status_code == 404
    assert (
        _request(
            "PATCH",
            f"/api/v1/orders/{order_id}/cancel",
            token=token,
            body={"remarks": "unauthorized"},
        ).status_code
        == 404
    )


def test_customers_cannot_access_another_orders_tracking(security_context) -> None:
    response = _request(
        "GET",
        f"/api/v1/tracking/{security_context.ids['owned_order']}",
        token=security_context.tokens["other_customer"],
    )

    assert response.status_code == 404


def test_tracking_location_history_is_scoped_to_the_current_assignment(
    security_context,
) -> None:
    latest = _request(
        "GET",
        f"/api/v1/tracking/{security_context.ids['owned_order']}",
        token=security_context.tokens["customer"],
    )
    history = _request(
        "GET",
        f"/api/v1/tracking/{security_context.ids['owned_order']}/history",
        token=security_context.tokens["customer"],
    )

    assert latest.status_code == 200
    assert latest.json()["latitude"] == 5.6
    assert latest.json()["longitude"] == -0.18
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["latitude"] == 5.6

    unauthorized_history = _request(
        "GET",
        f"/api/v1/tracking/{security_context.ids['owned_order']}/history",
        token=security_context.tokens["other_customer"],
    )
    assert unauthorized_history.status_code == 404


def test_order_fee_is_calculated_by_the_server(security_context) -> None:
    response = _request(
        "POST",
        "/api/v1/orders",
        token=security_context.tokens["customer"],
        body={
            "pickup_address": "Pickup",
            "pickup_latitude": 5.6,
            "pickup_longitude": -0.18,
            "destination_address": "Destination",
            "destination_latitude": 5.61,
            "destination_longitude": -0.19,
            "recipient_name": "Receiver",
            "recipient_phone": "123456789",
            "package_description": "Parcel",
            "delivery_fee": "0.01",
        },
    )

    assert response.status_code == 201
    assert response.json()["delivery_fee"] == str(
        calculate_delivery_fee(5.6, -0.18, 5.61, -0.19)
    )
    assert response.json()["delivery_fee"] != "0.01"


def test_database_prevents_a_rider_from_holding_two_active_assignments(
    security_context,
) -> None:
    with security_context.session_factory() as db:
        rider_id = security_context.ids["owned_rider"]
        second_order = Order(
            customer_id=security_context.ids["customer_user"],
            tracking_number="SECOND-ACTIVE-ORDER-0004",
            pickup_address="Pickup",
            pickup_latitude=5.6,
            pickup_longitude=-0.18,
            destination_address="Destination",
            destination_latitude=5.61,
            destination_longitude=-0.19,
            recipient_name="Recipient",
            recipient_phone="123456789",
            package_description="Second parcel",
            delivery_fee=10,
            current_status=OrderStatus.CONFIRMED,
        )
        db.add(second_order)
        db.flush()
        db.add(
            Assignment(
                order_id=second_order.id,
                rider_id=rider_id,
                dispatcher_id=security_context.ids["dispatcher_user"],
                assignment_status=AssignmentStatus.PENDING,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_customers_request_delivery_codes_without_persisting_plaintext(
    security_context,
) -> None:
    unauthorized = _request(
        "POST",
        f"/api/v1/orders/{security_context.ids['owned_order']}/delivery-code",
        token=security_context.tokens["other_customer"],
    )
    assert unauthorized.status_code == 404

    codes = []
    for _ in range(2):
        response = _request(
            "POST",
            f"/api/v1/orders/{security_context.ids['owned_order']}/delivery-code",
            token=security_context.tokens["customer"],
        )
        assert response.status_code == 201
        code = response.json()["verification_code"]
        assert len(code) == 6 and code.isdigit()
        codes.append(code)

    limited = _request(
        "POST",
        f"/api/v1/orders/{security_context.ids['owned_order']}/delivery-code",
        token=security_context.tokens["customer"],
    )
    assert limited.status_code == 429

    with security_context.session_factory() as db:
        proofs = sorted(
            db.scalars(
                select(DeliveryProof).where(
                    DeliveryProof.order_id == security_context.ids["owned_order"]
                )
            ).all(),
            key=lambda proof: proof.id,
        )
        notifications = list(db.scalars(select(Notification)).all())
        assert len(proofs) == 3
        assert all(
            code not in notification.message for code in codes for notification in notifications
        )
        assert all(
            proof.verification_code_hash not in codes
            and proof.verification_code_hash.startswith("$argon2id$")
            for proof in proofs
        )
        assert all(
            proof.code_expires_at < proofs[-1].code_expires_at
            for proof in proofs[:-1]
        )


def test_verification_attempt_limit_is_shared_across_code_requests(security_context) -> None:
    for _ in range(4):
        response = _request(
            "POST",
            f"/api/v1/rider/orders/{security_context.ids['owned_order']}/proof",
            token=security_context.tokens["rider"],
            body={
                "image_url": "https://example.com/proof.jpg",
                "verification_code": "000000",
            },
        )
        assert response.status_code == 400

    code = _request(
        "POST",
        f"/api/v1/orders/{security_context.ids['owned_order']}/delivery-code",
        token=security_context.tokens["customer"],
    )
    assert code.status_code == 201
    final_attempt = _request(
        "POST",
        f"/api/v1/rider/orders/{security_context.ids['owned_order']}/proof",
        token=security_context.tokens["rider"],
        body={
            "image_url": "https://example.com/proof.jpg",
            "verification_code": "000000",
        },
    )
    assert final_attempt.status_code == 429


def test_rider_cannot_update_an_unassigned_order(security_context) -> None:
    response = _request(
        "PATCH",
        f"/api/v1/rider/orders/{security_context.ids['other_order']}/status",
        token=security_context.tokens["rider"],
        body={"status": "in_transit"},
    )

    assert response.status_code == 404


def test_non_dispatcher_cannot_call_dispatch_endpoints(security_context) -> None:
    for role in ("customer", "rider"):
        response = _request(
            "GET",
            "/api/v1/dispatch/orders",
            token=security_context.tokens[role],
        )
        assert response.status_code == 403


def test_passwords_use_argon2_and_short_passwords_are_rejected() -> None:
    encoded = hash_password("at-least-eight-characters")

    assert encoded.startswith("$argon2id$")
    assert verify_password("at-least-eight-characters", encoded)
    assert not verify_password("incorrect", encoded)
    with pytest.raises(ValidationError):
        UserCreate(email="short@example.com", password="short")


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        jwt.encode(
            {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
            "a-different-secret-with-more-than-32-characters",
            algorithm="HS256",
        ),
        jwt.encode(
            {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
            TEST_SECRET,
            algorithm="HS256",
        ),
    ],
)
def test_invalid_tampered_and_expired_tokens_are_rejected(security_context, token) -> None:
    response = _request("GET", "/api/v1/auth/me", token=token)

    assert response.status_code == 401


def test_tracking_lookup_and_order_validation_resist_injection(security_context) -> None:
    tracking = _request(
        "GET",
        "/api/v1/orders/track/%27%20OR%201%3D1--",
    )
    assert tracking.status_code == 404

    invalid_coordinates = _request(
        "POST",
        "/api/v1/orders",
        token=security_context.tokens["customer"],
        body={
            "pickup_address": "Pickup",
            "pickup_latitude": 91,
            "pickup_longitude": 0,
            "destination_address": "Destination",
            "destination_latitude": 0,
            "destination_longitude": 0,
            "recipient_name": "Receiver",
            "recipient_phone": "123456789",
            "package_description": "Parcel",
            "delivery_fee": 10,
        },
    )
    assert invalid_coordinates.status_code == 422

    malformed_body = _request(
        "POST",
        "/api/v1/orders",
        token=security_context.tokens["customer"],
        body={"pickup_address": "missing required fields"},
    )
    assert malformed_body.status_code == 422


def test_delivery_verification_stores_hash_and_limits_failed_attempts(
    security_context,
) -> None:
    with security_context.session_factory() as db:
        proof = db.scalar(
            select(DeliveryProof).where(
                DeliveryProof.order_id == security_context.ids["owned_order"]
            )
        )
        assert proof is not None
        assert proof.verification_code_hash != "123456"
        assert proof.verification_code_hash.startswith("$argon2id$")

    for attempt in range(5):
        response = _request(
            "POST",
            f"/api/v1/rider/orders/{security_context.ids['owned_order']}/proof",
            token=security_context.tokens["rider"],
            body={
                "image_url": "https://example.com/proof.jpg",
                "verification_code": "000000",
            },
        )
        assert response.status_code == (429 if attempt == 4 else 400)

    response = _request(
        "POST",
        f"/api/v1/rider/orders/{security_context.ids['owned_order']}/proof",
        token=security_context.tokens["rider"],
        body={
            "image_url": "https://example.com/proof.jpg",
            "verification_code": "000000",
        },
    )
    assert response.status_code == 429


def test_expired_delivery_verification_code_is_rejected(security_context) -> None:
    with security_context.session_factory() as db:
        proof = db.scalar(
            select(DeliveryProof).where(
                DeliveryProof.order_id == security_context.ids["owned_order"]
            )
        )
        assert proof is not None
        proof.code_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    response = _request(
        "POST",
        f"/api/v1/rider/orders/{security_context.ids['owned_order']}/proof",
        token=security_context.tokens["rider"],
        body={
            "image_url": "https://example.com/proof.jpg",
            "verification_code": "123456",
        },
    )

    assert response.status_code == 409
