from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.connection import get_db
from app.dependencies.authentication import require_roles
from app.models.rider_profile import RiderAvailability, RiderProfile
from app.models.user import AccountStatus, User, UserRole
from app.schemas.user import AdminUserCreate, UserResponse

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    return list(
        db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
) -> User:
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        role=payload.role,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    if payload.role == UserRole.RIDER:
        db.add(
            RiderProfile(
                user_id=user.id,
                vehicle_type=payload.vehicle_type,
                vehicle_registration=payload.vehicle_registration,
                availability_status=RiderAvailability.UNAVAILABLE,
            )
        )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/approve", response_model=UserResponse)
def approve_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role not in {UserRole.DISPATCHER, UserRole.RIDER}:
        raise HTTPException(
            status_code=400,
            detail="Only dispatcher and rider accounts require approval",
        )
    if not user.is_verified or user.account_status != AccountStatus.ACTIVE:
        user.is_verified = True
        user.account_status = AccountStatus.ACTIVE
        db.commit()
        db.refresh(user)
    return user


@router.patch("/{user_id}/reject", response_model=UserResponse)
def reject_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role not in {UserRole.DISPATCHER, UserRole.RIDER} or user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Only pending dispatcher and rider accounts can be rejected",
        )
    if user.account_status != AccountStatus.SUSPENDED:
        user.account_status = AccountStatus.SUSPENDED
        db.commit()
        db.refresh(user)
    return user
