import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class DeliveryPoolStatus(str, enum.Enum):
    OPEN = "OPEN"
    DISPATCHED = "DISPATCHED"
    CLOSED = "CLOSED"


class DeliveryPool(Base):
    __tablename__ = "delivery_pools"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    zone_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dropoff_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_lng: Mapped[float] = mapped_column(Float, nullable=False)
    total_base_fee: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[DeliveryPoolStatus] = mapped_column(
        Enum(DeliveryPoolStatus, name="delivery_pool_status_enum"),
        default=DeliveryPoolStatus.OPEN,
        nullable=False,
        index=True,
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="pool")
