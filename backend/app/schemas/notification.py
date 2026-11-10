from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryProofResponse(BaseModel):
    id: int
    order_id: int
    image_url: str | None
    verified_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
