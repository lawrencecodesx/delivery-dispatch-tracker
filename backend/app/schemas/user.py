from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.user import AccountStatus, UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=30)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CUSTOMER
    vehicle_type: str | None = Field(default=None, min_length=1, max_length=50)
    vehicle_registration: str | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_public_role(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value

    @model_validator(mode="after")
    def validate_registration_role_fields(self) -> "UserCreate":
        if self.role == UserRole.RIDER and (
            self.vehicle_type is None or self.vehicle_registration is None
        ):
            raise ValueError("Rider registration requires vehicle type and registration")
        if self.role != UserRole.RIDER and (
            self.vehicle_type is not None or self.vehicle_registration is not None
        ):
            raise ValueError("Vehicle details are only valid for rider registration")
        return self


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_verified: bool
    account_status: AccountStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RiderRegistration(BaseModel):
    vehicle_type: str = Field(min_length=1, max_length=50)
    vehicle_registration: str = Field(min_length=1, max_length=30)


class AdminUserCreate(UserCreate):
    role: UserRole
    vehicle_type: str | None = Field(default=None, min_length=1, max_length=50)
    vehicle_registration: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def require_rider_vehicle(self) -> "AdminUserCreate":
        if self.role == UserRole.RIDER and (
            self.vehicle_type is None or self.vehicle_registration is None
        ):
            raise ValueError("Rider accounts require vehicle type and registration")
        if self.role != UserRole.RIDER and (
            self.vehicle_type is not None or self.vehicle_registration is not None
        ):
            raise ValueError("Vehicle details are only valid for rider accounts")
        return self