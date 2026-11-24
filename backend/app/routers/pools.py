import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.database.connection import get_db
from app.dependencies.authentication import get_current_user, require_roles
from app.models.delivery_pool import DeliveryPool, DeliveryPoolStatus
from app.models.delivery_proof import DeliveryProof
from app.models.order import CargoTier, Order, OrderStatus
from app.models.user import User, UserRole
from app.schemas.pool import (
    DeliveryPoolCreate,
    DeliveryPoolResponse,
    PoolJoinCreate,
    PoolJoinResponse,
)
from app.services.audit_service import append_status_history
from app.services.pricing import calculate_sla_deadline

router = APIRouter(prefix="/api/v1/pools", tags=["pools"])


def _pool_response(db: Session, pool: DeliveryPool) -> DeliveryPoolResponse:
    orders = db.scalars(select(Order).where(Order.pool_id == pool.id)).all()
    participant_count = len(orders)
    split_fee = round(pool.total_base_fee / max(participant_count, 1), 2)
    return DeliveryPoolResponse(
        id=pool.id,
        zone_name=pool.zone_name,
        dropoff_lat=pool.dropoff_lat,
        dropoff_lng=pool.dropoff_lng,
        total_base_fee=pool.total_base_fee,
        expires_at=pool.expires_at,
        status=pool.status,
        participant_count=participant_count,
        split_fee_ghs=split_fee,
    )


@router.get("", response_model=list[DeliveryPoolResponse])
def list_open_pools(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[DeliveryPoolResponse]:
    pools = db.scalars(
        select(DeliveryPool)
        .where(
            DeliveryPool.status == DeliveryPoolStatus.OPEN,
            DeliveryPool.expires_at > datetime.now(UTC),
        )
        .order_by(DeliveryPool.expires_at)
    ).all()
    return [_pool_response(db, pool) for pool in pools]


@router.post("", response_model=DeliveryPoolResponse, status_code=status.HTTP_201_CREATED)
def create_pool(
    payload: DeliveryPoolCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.DISPATCHER, UserRole.ADMIN)),
) -> DeliveryPoolResponse:
    pool = DeliveryPool(
        zone_name=payload.zone_name,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        total_base_fee=payload.total_base_fee,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
        status=DeliveryPoolStatus.OPEN,
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return _pool_response(db, pool)


@router.post("/{pool_id}/join", response_model=PoolJoinResponse, status_code=201)
def join_pool(
    pool_id: int,
    payload: PoolJoinCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> PoolJoinResponse:
    pool = db.scalar(
        select(DeliveryPool).where(DeliveryPool.id == pool_id).with_for_update()
    )
    now = datetime.now(UTC)
    if pool is None:
        raise HTTPException(status_code=404, detail="Delivery pool not found")
    expires_at = pool.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if pool.status != DeliveryPoolStatus.OPEN or expires_at <= now:
        raise HTTPException(status_code=409, detail="This delivery pool is no longer open")
    existing = db.scalar(
        select(Order.id).where(Order.pool_id == pool.id, Order.customer_id == user.id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already joined this pool")

    tracking_number = secrets.token_hex(16).upper()
    while db.scalar(select(Order.id).where(Order.tracking_number == tracking_number)):
        tracking_number = secrets.token_hex(16).upper()
    participant_count = (
        len(db.scalars(select(Order.id).where(Order.pool_id == pool.id)).all()) + 1
    )
    split_fee = round(pool.total_base_fee / participant_count, 2)
    order = Order(
        customer_id=user.id,
        tracking_number=tracking_number,
        pickup_address=payload.pickup_address,
        pickup_latitude=payload.pickup_latitude,
        pickup_longitude=payload.pickup_longitude,
        destination_address=pool.zone_name,
        destination_latitude=pool.dropoff_lat,
        destination_longitude=pool.dropoff_lng,
        recipient_name=payload.recipient_name,
        recipient_phone=payload.recipient_phone,
        package_description=payload.package_description,
        delivery_fee=Decimal(str(split_fee)),
        current_status=OrderStatus.PENDING,
        created_at=now,
        cargo_tier=payload.cargo_tier,
        max_temp_c=(
            payload.max_temp_c
            if payload.max_temp_c is not None
            else 8.0
            if payload.cargo_tier == CargoTier.COLD_CHAIN
            else None
        ),
        pool_id=pool.id,
        split_fee_ghs=split_fee,
        sla_deadline=calculate_sla_deadline(
            payload.pickup_latitude,
            payload.pickup_longitude,
            pool.dropoff_lat,
            pool.dropoff_lng,
            now,
        ),
    )
    db.add(order)
    db.flush()
    for participant in db.scalars(
        select(Order).where(Order.pool_id == pool.id).with_for_update()
    ):
        participant.split_fee_ghs = split_fee
        participant.delivery_fee = Decimal(str(split_fee))
    append_status_history(
        db,
        order_id=order.id,
        actor_id=user.id,
        old_status=None,
        new_status=OrderStatus.PENDING,
        remarks="Joined campus delivery pool",
        timestamp=now,
    )
    prior_proofs = db.scalars(
        select(DeliveryProof)
        .join(Order, DeliveryProof.order_id == Order.id)
        .where(Order.pool_id == pool.id)
    ).all()
    otp = f"{secrets.randbelow(1_000_000):06d}"
    while any(verify_password(otp, proof.verification_code_hash) for proof in prior_proofs):
        otp = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        DeliveryProof(
            order_id=order.id,
            verification_code_hash=hash_password(otp),
            code_expires_at=now + timedelta(days=1),
        )
    )
    db.commit()
    return PoolJoinResponse(
        order_id=order.id,
        tracking_number=order.tracking_number,
        verification_otp=otp,
        split_fee_ghs=split_fee,
        participant_count=participant_count,
    )
