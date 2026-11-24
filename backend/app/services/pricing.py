from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from math import asin, cos, radians, sin, sqrt

BASE_DELIVERY_FEE = Decimal("5.00")
DELIVERY_RATE_PER_KM = Decimal("1.50")
EARTH_RADIUS_KM = 6371.0
CENT = Decimal("0.01")


def calculate_delivery_fee(
    pickup_latitude: float,
    pickup_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> Decimal:
    latitude_delta = radians(destination_latitude - pickup_latitude)
    longitude_delta = radians(destination_longitude - pickup_longitude)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(pickup_latitude))
        * cos(radians(destination_latitude))
        * sin(longitude_delta / 2) ** 2
    )
    distance_km = 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, haversine)))
    fee = BASE_DELIVERY_FEE + DELIVERY_RATE_PER_KM * Decimal(str(distance_km))
    return fee.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_sla_deadline(
    pickup_latitude: float,
    pickup_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    created_at: datetime | None = None,
) -> datetime:
    latitude_delta = radians(destination_latitude - pickup_latitude)
    longitude_delta = radians(destination_longitude - pickup_longitude)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(pickup_latitude))
        * cos(radians(destination_latitude))
        * sin(longitude_delta / 2) ** 2
    )
    distance_km = 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, haversine)))
    start = created_at or datetime.now(UTC)
    return start + timedelta(minutes=20 + distance_km * 3)
