from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.assignment import AssignmentStatus
from app.models.order import OrderStatus
from app.models.rider_profile import RiderAvailability
from app.schemas.order import OrderResponse


class RiderProfileCreate(BaseModel):
    user_id: int = Field(gt=0)
    vehicle_type: str = Field(min_length=1, max_length=50)
    vehicle_registration: str = Field(min_length=1, max_length=30)


class RiderProfileResponse(BaseModel):
    id: int
    user_id: int
    vehicle_type: str
    vehicle_registration: str
    availability_status: RiderAvailability

    model_config = ConfigDict(from_attributes=True)


class AssignmentResponse(BaseModel):
    id: int
    order_id: int
    rider_id: int
    assigned_at: datetime
    accepted_at: datetime | None
    assignment_status: AssignmentStatus
    order: OrderResponse

    model_config = ConfigDict(from_attributes=True)


class AssignmentDecision(BaseModel):
    decision: str = Field(pattern="^(accept|reject)$")
    remarks: str | None = Field(default=None, max_length=1000)


class RiderStatusUpdate(BaseModel):
    status: OrderStatus
    remarks: str | None = Field(default=None, max_length=1000)


class AvailabilityUpdate(BaseModel):
    availability_status: RiderAvailability


class DeliveryProofCreate(BaseModel):
    image_url: HttpUrl
    verification_code: str = Field(pattern="^[0-9]{6}$")


class RiderLocationCreate(BaseModel):
    order_id: int = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    recorded_at: datetime | None = None
    accuracy: float | None = Field(default=None, ge=0)


class RiderLocationResponse(BaseModel):
    id: int
    rider_id: int
    latitude: float
    longitude: float
    recorded_at: datetime
    accuracy: float | None

    model_config = ConfigDict(from_attributes=True)
