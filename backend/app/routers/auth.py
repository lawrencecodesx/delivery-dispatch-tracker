from ipaddress import ip_address
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.database.connection import get_db
from app.dependencies.authentication import create_access_token, get_current_user
from app.models.rider_profile import RiderAvailability, RiderProfile
from app.models.user import AccountStatus, User, UserRole
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    if payload.role == UserRole.ADMIN or (
        payload.role != UserRole.CUSTOMER
        and not _public_role_registration_allowed(request)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public dispatcher and rider registration is available only from local development",
        )
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        role=payload.role,
        is_verified=payload.role == UserRole.CUSTOMER,
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


def _public_role_registration_allowed(request: Request) -> bool:
    if settings.APP_ENV != "development" or not settings.ALLOW_PUBLIC_ROLE_REGISTRATION:
        return False
    if request.client is None:
        return False
    try:
        if ip_address(request.client.host).is_loopback:
            return True
    except ValueError:
        pass

    origin = request.headers.get("origin")
    if origin not in settings.CORS_ALLOWED_ORIGINS:
        return False
    try:
        return urlsplit(origin).hostname in {"localhost", "127.0.0.1", "::1"} and (
            request.url.hostname in {"localhost", "127.0.0.1", "::1"}
        )
    except ValueError:
        return False


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="This account is suspended")
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending administrator approval.",
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user