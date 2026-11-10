from datetime import datetime

from pydantic import BaseModel


class TrackingLocationResponse(BaseModel):
    order_id: int
    latitude: float
    longitude: float
    accuracy: float | None
    recorded_at: datetime