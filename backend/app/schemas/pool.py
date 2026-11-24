from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.delivery_pool import DeliveryPoolStatus
from app.models.order import CargoTier


class DeliveryPoolCreate(BaseModel):
    zone_name: str = Field(min_length=3, max_length=200)
    dropoff_lat: float = Field(ge=-90, le=90)
    dropoff_lng: float = Field(ge=-180, le=180)
    total_base_fee: float = Field(gt=0)


class PoolJoinCreate(BaseModel):
    pickup_address: str = Field(min_length=3, max_length=500)
    pickup_latitude: float = Field(ge=-90, le=90)
    pickup_longitude: float = Field(ge=-180, le=180)
    recipient_name: str = Field(min_length=1, max_length=120)
    recipient_phone: str = Field(min_length=5, max_length=30)
    package_description: str = Field(min_length=1, max_length=2000)
    cargo_tier: CargoTier = CargoTier.STANDARD
    max_temp_c: float | None = Field(default=None, ge=-50, le=50)


class DeliveryPoolResponse(BaseModel):
    id: int
    zone_name: str
    dropoff_lat: float
    dropoff_lng: float
    total_base_fee: float
    expires_at: datetime
    status: DeliveryPoolStatus
    participant_count: int
    split_fee_ghs: float

    model_config = ConfigDict(from_attributes=True)


class PoolJoinResponse(BaseModel):
    order_id: int
    tracking_number: str
    verification_otp: str
    split_fee_ghs: float
    participant_count: int
