import argparse
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.base import Base
from app.database.connection import SessionLocal, engine
from app.models.assignment import Assignment, AssignmentStatus
from app.models.delivery_pool import DeliveryPool, DeliveryPoolStatus
from app.models.delivery_proof import DeliveryProof
from app.models.notification import Notification
from app.models.order import CargoTier, Order, OrderStatus
from app.models.order_history import OrderStatusHistory
from app.models.review import Review
from app.models.rider_location import RiderLocation
from app.models.rider_profile import RiderAvailability, RiderProfile
from app.models.user import AccountStatus, User, UserRole
from app.services.audit_service import append_status_history
from app.services.pricing import calculate_sla_deadline

DEMO_PASSWORD = "Password123!"
TRACKING_PREFIX = "DDT-DEMO-"
OTP_CODES = ("001234", "004321", "005678", "002468")
ORDER_FIELDS = (
    "tracking_number",
    "pickup_address",
    "pickup_latitude",
    "pickup_longitude",
    "destination_address",
    "destination_latitude",
    "destination_longitude",
    "recipient_name",
    "recipient_phone",
    "package_description",
    "delivery_fee",
    "current_status",
    "created_at",
)

USERS = [
    ("admin@dispatch.com", "Demo Administrator", UserRole.ADMIN, True, None),
    ("nora.admin@dispatch.com", "Nora Admin", UserRole.ADMIN, True, None),
    ("dispatcher@dispatch.com", "Kwame Dispatcher", UserRole.DISPATCHER, True, None),
    ("accra.dispatch@dispatch.com", "Accra Dispatcher", UserRole.DISPATCHER, True, None),
    ("pending.dispatch@dispatch.com", "Pending Dispatcher", UserRole.DISPATCHER, False, None),
    ("rider1@dispatch.com", "Kofi Mensah", UserRole.RIDER, True, "Osu, Accra"),
    ("rider2@dispatch.com", "Ama Owusu", UserRole.RIDER, True, "East Legon, Accra"),
    ("rider3@dispatch.com", "Yaw Boateng", UserRole.RIDER, True, "Airport City, Accra"),
    ("rider4@dispatch.com", "Efua Asante", UserRole.RIDER, True, "Madina, Accra"),
    ("rider5@dispatch.com", "Kojo Appiah", UserRole.RIDER, True, "UCC Campus, Cape Coast"),
    ("rider6@dispatch.com", "Abena Osei", UserRole.RIDER, True, "Abura, Cape Coast"),
    ("pending.rider1@dispatch.com", "Pending Rider One", UserRole.RIDER, False, None),
    ("pending.rider2@dispatch.com", "Pending Rider Two", UserRole.RIDER, False, None),
    ("customer@dispatch.com", "Ama Mensah", UserRole.CUSTOMER, True, None),
    ("kwame.mensah@dispatch.com", "Kwame Mensah", UserRole.CUSTOMER, True, None),
    ("ama.osei@dispatch.com", "Ama Osei", UserRole.CUSTOMER, True, None),
    ("kofi.boateng@dispatch.com", "Kofi Boateng", UserRole.CUSTOMER, True, None),
    ("efua.appiah@dispatch.com", "Efua Appiah", UserRole.CUSTOMER, True, None),
    ("yaw.asante@dispatch.com", "Yaw Asante", UserRole.CUSTOMER, True, None),
]

ACCRA_PLACES = [
    ("Osu Oxford Street, Accra", Decimal("5.557109"), Decimal("-0.183806")),
    ("East Legon, Accra", Decimal("5.650000"), Decimal("-0.166000")),
    ("Kotoka International Airport, Accra", Decimal("5.605186"), Decimal("-0.166786")),
    ("Madina Zongo Junction, Accra", Decimal("5.668500"), Decimal("-0.169500")),
    ("Cantonments, Accra", Decimal("5.570500"), Decimal("-0.176500")),
    ("Labone, Accra", Decimal("5.559100"), Decimal("-0.174800")),
    ("Spintex Road, Accra", Decimal("5.621600"), Decimal("-0.145400")),
    ("Roman Ridge, Accra", Decimal("5.600200"), Decimal("-0.190000")),
]

CAPE_COAST_PLACES = [
    ("University of Cape Coast, Cape Coast", Decimal("5.112000"), Decimal("-1.291000")),
    ("Abura Market, Cape Coast", Decimal("5.105000"), Decimal("-1.246000")),
    ("Kotokuraba Market, Cape Coast", Decimal("5.105300"), Decimal("-1.247100")),
    ("Cape Coast Castle, Cape Coast", Decimal("5.103000"), Decimal("-1.246800")),
    ("Pedu Junction, Cape Coast", Decimal("5.115700"), Decimal("-1.269000")),
    ("Amamoma, Cape Coast", Decimal("5.133000"), Decimal("-1.282000")),
]

ACCRA_ROUTES = [
    (0, 2), (2, 1), (1, 3), (4, 5), (6, 7), (7, 0), (3, 1), (5, 6),
]
CAPE_COAST_ROUTES = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0),
]
RIDER_HOME_LOCATIONS = [
    (5.557109, -0.183806),
    (5.650000, -0.166000),
    (5.605186, -0.166786),
    (5.668500, -0.169500),
    (5.112000, -1.291000),
    (5.105000, -1.246000),
]
CUSTOMER_EMAILS = (
    "customer@dispatch.com",
    "kwame.mensah@dispatch.com",
    "ama.osei@dispatch.com",
    "kofi.boateng@dispatch.com",
    "efua.appiah@dispatch.com",
    "yaw.asante@dispatch.com",
)
RIDER_EMAILS = tuple(f"rider{number}@dispatch.com" for number in range(1, 7))
ACTIVE_STATUSES = (
    OrderStatus.ASSIGNED,
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
    OrderStatus.IN_TRANSIT,
    OrderStatus.IN_TRANSIT,
    OrderStatus.IN_TRANSIT,
)


def _order_statuses() -> list[OrderStatus]:
    return (
        [OrderStatus.PENDING] * 6
        + list(ACTIVE_STATUSES)
        + [OrderStatus.DELIVERED] * 12
        + [OrderStatus.CANCELLED]
    )


def _route_for(index: int):
    active_routes = {
        6: (ACCRA_PLACES, (0, 2)),
        7: (ACCRA_PLACES, (1, 3)),
        8: (ACCRA_PLACES, (2, 1)),
        9: (ACCRA_PLACES, (3, 0)),
        10: (CAPE_COAST_PLACES, (0, 1)),
        11: (CAPE_COAST_PLACES, (1, 0)),
    }
    if index in active_routes:
        places, (pickup_index, destination_index) = active_routes[index]
        return places[pickup_index], places[destination_index]

    if index < 6:
        routes, places = (
            (ACCRA_ROUTES, ACCRA_PLACES)
            if index % 3
            else (CAPE_COAST_ROUTES, CAPE_COAST_PLACES)
        )
    else:
        routes, places = (
            (ACCRA_ROUTES, ACCRA_PLACES)
            if index % 2
            else (CAPE_COAST_ROUTES, CAPE_COAST_PLACES)
        )

    pickup_index, destination_index = routes[index % len(routes)]
    return places[pickup_index], places[destination_index]


def _order_specs(now: datetime) -> list[dict]:
    specs = []
    for index, status in enumerate(_order_statuses()):
        if index == 6:
            status = OrderStatus.PENDING
        pickup, destination = _route_for(index)
        if status == OrderStatus.DELIVERED:
            created_at = now - timedelta(days=(index - 12) % 7, hours=2 + index % 5)
        elif status == OrderStatus.CANCELLED:
            created_at = now - timedelta(days=2)
        else:
            created_at = now - timedelta(hours=1 + (index * 17) % 36)

        specs.append(
            {
                "tracking_number": f"{TRACKING_PREFIX}{index + 1:03d}",
                "pickup_address": pickup[0],
                "pickup_latitude": pickup[1],
                "pickup_longitude": pickup[2],
                "destination_address": destination[0],
                "destination_latitude": destination[1],
                "destination_longitude": destination[2],
                "recipient_name": USERS[13 + index % len(CUSTOMER_EMAILS)][1],
                "recipient_phone": f"+233 20 555 {1000 + index:04d}",
                "package_description": (
                    "Documents and office supplies",
                    "Fresh market produce",
                    "Clothing and personal items",
                    "Small electronics",
                    "Books and study materials",
                    "Packaged household goods",
                )[index % 6],
                "delivery_fee": Decimal(str(25 + (index * 11) % 61)),
                "current_status": status,
                "created_at": created_at,
                "rider_index": (
                    index - 6
                    if 6 <= index <= 11
                    and status in {
                        OrderStatus.ASSIGNED,
                        OrderStatus.PICKED_UP,
                        OrderStatus.IN_TRANSIT,
                    }
                    else None
                ),
                "otp": OTP_CODES[index - 8] if 8 <= index <= 11 else None,
            }
        )
    return specs


def _get_or_create_user(
    db: Session,
    email: str,
    full_name: str,
    role: UserRole,
    is_verified: bool,
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, hashed_password=hash_password(DEMO_PASSWORD))
        db.add(user)

    user.full_name = full_name
    user.hashed_password = hash_password(DEMO_PASSWORD)
    user.role = role
    user.is_verified = is_verified
    user.account_status = AccountStatus.ACTIVE
    db.flush()
    return user


def _get_or_create_rider_profile(db: Session, user: User, index: int) -> RiderProfile:
    profile = db.scalar(select(RiderProfile).where(RiderProfile.user_id == user.id))
    if profile is None:
        profile = RiderProfile(user_id=user.id)
        db.add(profile)

    profile.vehicle_type = "Motorbike"
    profile.vehicle_registration = f"GT-{1001 + index:04d}-26"
    profile.availability_status = RiderAvailability.AVAILABLE
    db.flush()
    return profile


def _clear_order_children(db: Session, order_ids: list[int]) -> None:
    if not order_ids:
        return

    assignment_ids = select(Assignment.id).where(Assignment.order_id.in_(order_ids))
    db.execute(
        delete(RiderLocation).where(RiderLocation.assignment_id.in_(assignment_ids))
    )
    db.execute(delete(DeliveryProof).where(DeliveryProof.order_id.in_(order_ids)))
    db.execute(delete(OrderStatusHistory).where(OrderStatusHistory.order_id.in_(order_ids)))
    db.execute(delete(Review).where(Review.order_id.in_(order_ids)))
    db.execute(delete(Assignment).where(Assignment.order_id.in_(order_ids)))


def _add_order_history(
    db: Session, order: Order, dispatcher: User, created_at: datetime
) -> None:
    append_status_history(
        db,
        order_id=order.id,
        actor_id=dispatcher.id,
        old_status=None,
        new_status=OrderStatus.PENDING,
        remarks="Demo seed order created",
        timestamp=created_at,
    )
    if order.current_status == OrderStatus.PENDING:
        return

    status_paths = {
        OrderStatus.ASSIGNED: [OrderStatus.CONFIRMED, OrderStatus.ASSIGNED],
        OrderStatus.PICKED_UP: [
            OrderStatus.CONFIRMED,
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.PICKED_UP,
        ],
        OrderStatus.IN_TRANSIT: [
            OrderStatus.CONFIRMED,
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.PICKED_UP,
            OrderStatus.IN_TRANSIT,
        ],
        OrderStatus.DELIVERED: [
            OrderStatus.CONFIRMED,
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.PICKED_UP,
            OrderStatus.IN_TRANSIT,
            OrderStatus.DELIVERED,
        ],
        OrderStatus.CANCELLED: [OrderStatus.CANCELLED],
    }
    previous_status = OrderStatus.PENDING
    path = status_paths.get(order.current_status, [])
    for step, next_status in enumerate(path):
        append_status_history(
            db,
            order_id=order.id,
            actor_id=dispatcher.id,
            old_status=previous_status,
            new_status=next_status,
            remarks="Demo seed status history",
            timestamp=created_at + timedelta(minutes=(step + 1) * 5),
        )
        previous_status = next_status


def _seed_order(
    db: Session,
    spec: dict,
    customer: User,
    dispatchers: tuple[User, User],
    rider_profiles: list[RiderProfile],
    now: datetime,
) -> None:
    order = db.scalar(
        select(Order).where(Order.tracking_number == spec["tracking_number"])
    )
    order_values = {field: spec[field] for field in ORDER_FIELDS}
    if order is None:
        order = Order(customer_id=customer.id, **order_values)
        db.add(order)
    else:
        order.customer_id = customer.id
        for field, value in order_values.items():
            setattr(order, field, value)
    order.cargo_tier = spec.get("cargo_tier", CargoTier.STANDARD)
    order.max_temp_c = spec.get("max_temp_c")
    order.sla_deadline = calculate_sla_deadline(
        float(spec["pickup_latitude"]),
        float(spec["pickup_longitude"]),
        float(spec["destination_latitude"]),
        float(spec["destination_longitude"]),
        spec["created_at"],
    )
    order.is_compromised = False
    order.sla_breached = False
    order.rebate_credited_ghs = 0.0
    order.pool_id = None
    order.split_fee_ghs = None
    db.flush()

    _add_order_history(
        db,
        order,
        dispatchers[int(spec["tracking_number"][-3:]) % len(dispatchers)],
        spec["created_at"],
    )

    rider_index = spec["rider_index"]
    if rider_index is None:
        return

    rider_profile = rider_profiles[rider_index]
    accepted = spec["current_status"] != OrderStatus.ASSIGNED
    assignment = Assignment(
        order_id=order.id,
        rider_id=rider_profile.id,
        dispatcher_id=dispatchers[rider_index % len(dispatchers)].id,
        assigned_at=spec["created_at"] + timedelta(minutes=5),
        accepted_at=spec["created_at"] + timedelta(minutes=10) if accepted else None,
        assignment_status=(
            AssignmentStatus.COMPLETED
            if spec["current_status"] == OrderStatus.DELIVERED
            else AssignmentStatus.ACCEPTED
            if accepted
            else AssignmentStatus.PENDING
        ),
    )
    db.add(assignment)
    db.flush()

    if spec["current_status"] == OrderStatus.IN_TRANSIT:
        db.add(
            DeliveryProof(
                order_id=order.id,
                verification_code_hash=hash_password(spec["otp"]),
                code_expires_at=now + timedelta(days=1),
            )
        )

    if spec["current_status"] in {
        OrderStatus.ASSIGNED,
        OrderStatus.PICKED_UP,
        OrderStatus.IN_TRANSIT,
    }:
        pickup_latitude = float(spec["pickup_latitude"])
        pickup_longitude = float(spec["pickup_longitude"])
        destination_latitude = float(spec["destination_latitude"])
        destination_longitude = float(spec["destination_longitude"])
        progress = 0.05 if spec["current_status"] == OrderStatus.ASSIGNED else 0.35
        if spec["current_status"] == OrderStatus.IN_TRANSIT:
            progress = 0.6
        db.add(
            RiderLocation(
                rider_id=rider_profile.id,
                assignment_id=assignment.id,
                latitude=pickup_latitude
                + (destination_latitude - pickup_latitude) * progress,
                longitude=pickup_longitude
                + (destination_longitude - pickup_longitude) * progress,
                recorded_at=now - timedelta(minutes=2),
                accuracy=12.0,
            )
        )


def _seed_campus_features(
    db: Session,
    customers: tuple[User, User],
    dispatcher: User,
    rider_user: User,
    rider: RiderProfile,
    now: datetime,
) -> None:
    zone_name = "Valco Hall Gate — Split Pool"
    pool = db.scalar(select(DeliveryPool).where(DeliveryPool.zone_name == zone_name))
    if pool is None:
        pool = DeliveryPool(
            zone_name=zone_name,
            dropoff_lat=5.112000,
            dropoff_lng=-1.291000,
            total_base_fee=60.0,
            expires_at=now + timedelta(minutes=15),
            status=DeliveryPoolStatus.OPEN,
        )
        db.add(pool)
    else:
        pool.dropoff_lat = 5.112000
        pool.dropoff_lng = -1.291000
        pool.total_base_fee = 60.0
        pool.expires_at = now + timedelta(minutes=15)
        pool.status = DeliveryPoolStatus.OPEN
    db.flush()

    for index, customer in enumerate(customers, start=1):
        created_at = now - timedelta(minutes=index)
        tracking_number = f"{TRACKING_PREFIX}POOL-00{index}"
        order = Order(
            customer_id=customer.id,
            tracking_number=tracking_number,
            pickup_address=f"UCC Student Residence {index}",
            pickup_latitude=5.105 + index * 0.001,
            pickup_longitude=-1.246,
            destination_address=pool.zone_name,
            destination_latitude=pool.dropoff_lat,
            destination_longitude=pool.dropoff_lng,
            recipient_name=customer.full_name or "Campus Student",
            recipient_phone=f"+233 20 555 20{index:02d}",
            package_description="Campus drop-pool parcel",
            delivery_fee=Decimal("30.00"),
            current_status=OrderStatus.PENDING,
            created_at=created_at,
            cargo_tier=CargoTier.STANDARD,
            pool_id=pool.id,
            split_fee_ghs=30.0,
            sla_deadline=calculate_sla_deadline(
                5.105 + index * 0.001, -1.246, pool.dropoff_lat, pool.dropoff_lng, created_at
            ),
        )
        db.add(order)
        db.flush()
        append_status_history(
            db,
            order_id=order.id,
            actor_id=customer.id,
            old_status=None,
            new_status=OrderStatus.PENDING,
            remarks="Campus pool participant order created",
            timestamp=created_at,
        )

    cold_created_at = now - timedelta(minutes=5)
    cold_order = Order(
        customer_id=customers[0].id,
        tracking_number=f"{TRACKING_PREFIX}COLDCHAIN",
        pickup_address="UCC Science Market",
        pickup_latitude=5.105000,
        pickup_longitude=-1.246000,
        destination_address="UCC Valco Hall Gate",
        destination_latitude=5.112000,
        destination_longitude=-1.291000,
        recipient_name="Campus Cold-Chain Recipient",
        recipient_phone="+233 20 555 0099",
        package_description="Temperature-sensitive campus medicine",
        delivery_fee=Decimal("45.00"),
        current_status=OrderStatus.IN_TRANSIT,
        created_at=cold_created_at,
        cargo_tier=CargoTier.COLD_CHAIN,
        max_temp_c=8.0,
        sla_deadline=calculate_sla_deadline(
            5.105, -1.246, 5.112, -1.291, cold_created_at
        ),
    )
    db.add(cold_order)
    db.flush()
    status_path = (
        (None, OrderStatus.PENDING, dispatcher),
        (OrderStatus.PENDING, OrderStatus.CONFIRMED, dispatcher),
        (OrderStatus.CONFIRMED, OrderStatus.ASSIGNED, dispatcher),
        (OrderStatus.ASSIGNED, OrderStatus.ACCEPTED, rider_user),
        (OrderStatus.ACCEPTED, OrderStatus.PICKED_UP, rider_user),
        (OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT, rider_user),
    )
    for sequence, (old_status, new_status, actor) in enumerate(status_path):
        append_status_history(
            db,
            order_id=cold_order.id,
            actor_id=actor.id,
            old_status=old_status,
            new_status=new_status,
            remarks="Campus cold-chain demo history",
            timestamp=cold_created_at + timedelta(minutes=sequence),
        )
    assignment = Assignment(
        order_id=cold_order.id,
        rider_id=rider.id,
        dispatcher_id=dispatcher.id,
        assigned_at=cold_created_at + timedelta(minutes=1),
        accepted_at=cold_created_at + timedelta(minutes=2),
        assignment_status=AssignmentStatus.ACCEPTED,
    )
    db.add(assignment)
    db.flush()
    db.add(
        DeliveryProof(
            order_id=cold_order.id,
            verification_code_hash=hash_password("007777"),
            code_expires_at=now + timedelta(days=1),
        )
    )
    db.add(
        RiderLocation(
            rider_id=rider.id,
            assignment_id=assignment.id,
            latitude=5.11202,
            longitude=-1.29102,
            recorded_at=now - timedelta(seconds=10),
            accuracy=5.0,
            temperature_c=7.5,
            deviation_meters=0.0,
            is_off_route=False,
        )
    )
    rider.availability_status = RiderAvailability.ON_DELIVERY


def _reset_demo_orders(db: Session) -> None:
    demo_orders = db.scalars(
        select(Order).where(Order.tracking_number.like(f"{TRACKING_PREFIX}%"))
    ).all()
    order_ids = [order.id for order in demo_orders]
    _clear_order_children(db, order_ids)

    for order in demo_orders:
        db.delete(order)
    db.flush()

    legacy_pending_rider = db.scalar(
        select(User).where(User.email == "pending.rider@dispatch.com")
    )
    if legacy_pending_rider is not None:
        db.execute(
            delete(Notification).where(Notification.user_id == legacy_pending_rider.id)
        )
        db.execute(delete(RiderProfile).where(RiderProfile.user_id == legacy_pending_rider.id))
        db.execute(delete(User).where(User.id == legacy_pending_rider.id))


def seed(reset: bool = False) -> None:
    engine.echo = False
    Base.metadata.create_all(bind=engine)
    now = datetime.now(UTC)
    specs = _order_specs(now)

    with SessionLocal() as db:
        if reset:
            _reset_demo_orders(db)
        else:
            existing_demo_orders = db.scalars(
                select(Order).where(Order.tracking_number.like(f"{TRACKING_PREFIX}%"))
            ).all()
            _clear_order_children(db, [order.id for order in existing_demo_orders])

        seeded_tracking_numbers = {spec["tracking_number"] for spec in specs}
        stale_orders = db.scalars(
            select(Order).where(Order.tracking_number.like(f"{TRACKING_PREFIX}%"))
        ).all()
        stale_orders = [
            order
            for order in stale_orders
            if order.tracking_number not in seeded_tracking_numbers
        ]
        if stale_orders:
            _clear_order_children(db, [order.id for order in stale_orders])
            for order in stale_orders:
                db.delete(order)
            db.flush()

        users = {
            email: _get_or_create_user(db, email, name, role, verified)
            for email, name, role, verified, _ in USERS
        }
        dispatchers = (
            users["dispatcher@dispatch.com"],
            users["accra.dispatch@dispatch.com"],
        )
        rider_profiles = [
            _get_or_create_rider_profile(db, users[email], index)
            for index, email in enumerate(RIDER_EMAILS)
        ]
        for spec in specs:
            customer = users[CUSTOMER_EMAILS[int(spec["tracking_number"][-3:]) % 6]]
            _seed_order(db, spec, customer, dispatchers, rider_profiles, now)

        active_rider_indexes = {
            spec["rider_index"]
            for spec in specs
            if spec["current_status"]
            in {OrderStatus.ASSIGNED, OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT}
        }
        for index, profile in enumerate(rider_profiles):
            profile.availability_status = (
                RiderAvailability.ON_DELIVERY
                if index in active_rider_indexes
                else RiderAvailability.AVAILABLE
            )
            home_location = db.scalar(
                select(RiderLocation).where(
                    RiderLocation.rider_id == profile.id,
                    RiderLocation.assignment_id.is_(None),
                )
            )
            if home_location is None:
                home_location = RiderLocation(
                    rider_id=profile.id,
                    latitude=RIDER_HOME_LOCATIONS[index][0],
                    longitude=RIDER_HOME_LOCATIONS[index][1],
                    recorded_at=now - timedelta(minutes=20),
                    accuracy=25.0,
                )
                db.add(home_location)
            else:
                home_location.latitude = RIDER_HOME_LOCATIONS[index][0]
                home_location.longitude = RIDER_HOME_LOCATIONS[index][1]
                home_location.recorded_at = now - timedelta(minutes=20)
        _seed_campus_features(
            db,
            (
                users["customer@dispatch.com"],
                users["kwame.mensah@dispatch.com"],
            ),
            dispatchers[0],
            users["rider1@dispatch.com"],
            rider_profiles[0],
            now,
        )
        db.commit()

    print("Demo database seeding complete.")
    if reset:
        print("Previous DDT-DEMO orders and related records were cleared first.")
    print()
    print(f"{'Email':<34} {'Role':<12} {'Verified':<9} {'Password'}")
    print("-" * 88)
    for email, _, role, verified, _ in USERS:
        print(f"{email:<34} {role.value:<12} {verified!s:<9} {DEMO_PASSWORD}")

    print()
    print("Active delivery OTPs (six digits, matching rider API validation):")
    print(f"{'Tracking number':<22} {'Rider':<30} {'OTP'}")
    print("-" * 64)
    for spec in specs:
        if spec["otp"]:
            rider_email = RIDER_EMAILS[spec["rider_index"]]
            print(f"{spec['tracking_number']:<22} {rider_email:<30} {spec['otp']}")

    status_counts = Counter(spec["current_status"].value for spec in specs)
    print()
    print(f"{'Order status':<18} {'Count':>5}")
    print("-" * 25)
    for status in OrderStatus:
        count = status_counts.get(status.value, 0)
        if count:
            print(f"{status.value:<18} {count:>5}")
    print(f"{'TOTAL':<18} {len(specs):>5}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the demo delivery database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing DDT-DEMO orders and related records before reseeding.",
    )
    seed(reset=parser.parse_args().reset)
