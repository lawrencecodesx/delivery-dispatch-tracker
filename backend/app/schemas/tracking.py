from datetime import datetime

from pydantic import BaseModel


class TrackingLocationResponse(BaseModel):
    order_id: int
    latitude: float
    longitude: float
    accuracy: float | None
    recorded_at: datetime
    temperature_c: float | None = None
    deviation_meters: float = 0.0
    is_off_route: bool = False