from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.assignment import AssignmentStatus
from app.models.rider_profile import RiderAvailability
from app.schemas.order import OrderResponse


class OrderReviewRequest(BaseModel):
    decision: str = Field(pattern="^(confirm|reject)$")
    remarks: str | None = Field(default=None, max_length=1000)


class ReturnOrderRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=1000)


class AssignmentCreate(BaseModel):
    order_id: int = Field(gt=0)
    rider_id: int = Field(gt=0)


class AssignmentReassign(BaseModel):
    rider_id: int = Field(gt=0)


class AssignmentResponse(BaseModel):
    id: int
    order_id: int
    rider_id: int
    dispatcher_id: int
    assigned_at: datetime
    accepted_at: datetime | None
    assignment_status: AssignmentStatus

    model_config = ConfigDict(from_attributes=True)


class RiderCandidateResponse(BaseModel):
    rider_id: int
    user_id: int
    full_name: str | None
    vehicle_type: str
    vehicle_registration: str
    availability_status: RiderAvailability
    active_assignments: int
    distance_km: float | None = None


class AssignmentWithOrderResponse(AssignmentResponse):
    order: OrderResponse
