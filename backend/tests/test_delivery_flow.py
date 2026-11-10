import asyncio
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.database.base import Base
from app.database.connection import get_db
from app.dependencies.authentication import create_access_token
from app.main import app
from app.models import DeliveryProof, RiderAvailability, RiderProfile, User, UserRole
from app.services.pricing import calculate_delivery_fee


def test_customer_order_dispatch_rider_delivery_flow() -> None:
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

    previous_secret = settings.JWT_SECRET_KEY
    app.dependency_overrides[get_db] = override_db
    settings.JWT_SECRET_KEY = "test-secret-that-is-at-least-32-characters-long"
    try:
        with test_session() as db:
            customer = User(
                email="customer@example.com",
                hashed_password=hash_password("password-long"),
                role=UserRole.CUSTOMER,
            )
            dispatcher = User(
                email="dispatcher@example.com",
                hashed_password=hash_password("password-long"),
                role=UserRole.DISPATCHER,
            )
            rider_user = User(
                email="rider@example.com",
                hashed_password=hash_password("password-long"),
                role=UserRole.RIDER,
            )
            db.add_all([customer, dispatcher, rider_user])
            db.flush()
            db.add(
                RiderProfile(
                    user_id=rider_user.id,
                    vehicle_type="bike",
                    vehicle_registration="ABC-123",
                    availability_status=RiderAvailability.AVAILABLE,
                )
            )
            db.commit()
            customer_token = create_access_token(customer.id)
            dispatcher_token = create_access_token(dispatcher.id)
            rider_token = create_access_token(rider_user.id)

        async def run_flow() -> None:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                customer_headers = {"Authorization": f"Bearer {customer_token}"}
                dispatcher_headers = {"Authorization": f"Bearer {dispatcher_token}"}
                rider_headers = {"Authorization": f"Bearer {rider_token}"}
                response = await client.post(
                    "/api/v1/orders",
                    headers=customer_headers,
                    json={
                        "pickup_address": "Pickup 1",
                        "pickup_latitude": 5.6,
                        "pickup_longitude": -0.18,
                        "destination_address": "Destination 2",
                        "destination_latitude": 5.61,
                        "destination_longitude": -0.19,
                        "recipient_name": "Receiver",
                        "recipient_phone": "123456789",
                        "package_description": "Parcel",
                        "delivery_fee": "0.01",
                    },
                )
                assert response.status_code == 201, response.text
                order_id = response.json()["id"]
                assert Decimal(response.json()["delivery_fee"]) == calculate_delivery_fee(
                    5.6, -0.18, 5.61, -0.19
                )

                response = await client.patch(
                    f"/api/v1/dispatch/orders/{order_id}/review",
                    headers=dispatcher_headers,
                    json={"decision": "confirm"},
                )
                assert response.status_code == 200, response.text
                response = await client.get(
                    "/api/v1/dispatch/riders",
                    headers=dispatcher_headers,
                )
                assert response.status_code == 200, response.text
                candidates = response.json()
                assert len(candidates) == 1

                response = await client.post(
                    "/api/v1/dispatch/assignments",
                    headers=dispatcher_headers,
                    json={"order_id": order_id, "rider_id": candidates[0]["rider_id"]},
                )
                assert response.status_code == 201, response.text
                assignment_id = response.json()["id"]
                response = await client.patch(
                    f"/api/v1/rider/assignments/{assignment_id}/respond",
                    headers=rider_headers,
                    json={"decision": "accept"},
                )
                assert response.status_code == 200, response.text

                for order_status in ("picked_up", "in_transit"):
                    response = await client.patch(
                        f"/api/v1/rider/orders/{order_id}/status",
                        headers=rider_headers,
                        json={"status": order_status},
                    )
                    assert response.status_code == 200, response.text

                response = await client.post(
                    "/api/v1/rider/location",
                    headers=rider_headers,
                    json={
                        "order_id": order_id,
                        "latitude": 5.605,
                        "longitude": -0.185,
                    },
                )
                assert response.status_code == 201, response.text
                response = await client.get(
                    f"/api/v1/tracking/{order_id}", headers=customer_headers
                )
                assert response.status_code == 200, response.text
                assert response.json()["latitude"] == 5.605

                response = await client.post(
                    f"/api/v1/orders/{order_id}/delivery-code",
                    headers=customer_headers,
                )
                assert response.status_code == 201, response.text
                verification_code = response.json()["verification_code"]
                response = await client.get(
                    "/api/v1/notifications", headers=customer_headers
                )
                assert response.status_code == 200, response.text
                message = response.json()[0]["message"]
                assert verification_code not in message
                assert "tracking page" in message
                with test_session() as db:
                    proof = db.scalar(
                        select(DeliveryProof).where(DeliveryProof.order_id == order_id)
                    )
                    assert proof is not None
                    assert proof.verification_code_hash.startswith("$argon2id$")
                    assert proof.verification_code_hash != verification_code
                response = await client.post(
                    f"/api/v1/rider/orders/{order_id}/proof",
                    headers=rider_headers,
                    json={
                        "image_url": "https://example.com/proof.jpg",
                        "verification_code": verification_code,
                    },
                )
                assert response.status_code == 200, response.text
                response = await client.post(
                    f"/api/v1/orders/{order_id}/review",
                    headers=customer_headers,
                    json={"rating": 5, "comment": "Delivered"},
                )
                assert response.status_code == 201, response.text

        asyncio.run(run_flow())
    finally:
        settings.JWT_SECRET_KEY = previous_secret
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
