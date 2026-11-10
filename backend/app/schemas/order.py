from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.order import OrderStatus

Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
TrackingNumber = Annotated[str, StringConstraints(min_length=12, max_length=32)]


class OrderCreate(BaseModel):
    pickup_address: str = Field(min_length=3, max_length=500)
    pickup_latitude: Latitude
    pickup_longitude: Longitude
    destination_address: str = Field(min_length=3, max_length=500)
    destination_latitude: Latitude
    destination_longitude: Longitude
    recipient_name: str = Field(min_length=1, max_length=120)
    recipient_phone: str = Field(min_length=5, max_length=30)
    package_description: str = Field(min_length=1, max_length=2000)


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    tracking_number: str
    pickup_address: str
    pickup_latitude: float
    pickup_longitude: float
    destination_address: str
    destination_latitude: float
    destination_longitude: float
    recipient_name: str
    recipient_phone: str
    package_description: str
    delivery_fee: Decimal
    current_status: OrderStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    id: int
    updated_by: int
    previous_status: OrderStatus | None
    new_status: OrderStatus
    remarks: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(OrderResponse):
    status_history: list[OrderStatusHistoryResponse]


class PublicTrackingResponse(BaseModel):
    tracking_number: TrackingNumber
    current_status: OrderStatus
    created_at: datetime
    pickup_address: str
    destination_address: str
    updated_at: datetime | None = None


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class CancelOrderRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    order_id: int
    customer_id: int
    rider_id: int
    rating: int
    comment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryCodeResponse(BaseModel):
    verification_code: str
    expires_at: datetime
