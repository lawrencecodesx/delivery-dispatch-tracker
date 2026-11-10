import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.delivery_proof import DeliveryProof
    from app.models.order_history import OrderStatusHistory
    from app.models.review import Review
    from app.models.user import User


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


ORDER_STATUS_DB_TYPE = Enum(
    OrderStatus,
    name="order_status_enum",
    values_callable=lambda members: [member.value for member in members],
)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("delivery_fee >= 0", name="ck_orders_delivery_fee_nonnegative"),
        CheckConstraint(
            "pickup_latitude BETWEEN -90 AND 90", name="ck_orders_pickup_latitude"
        ),
        CheckConstraint(
            "pickup_longitude BETWEEN -180 AND 180", name="ck_orders_pickup_longitude"
        ),
        CheckConstraint(
            "destination_latitude BETWEEN -90 AND 90",
            name="ck_orders_destination_latitude",
        ),
        CheckConstraint(
            "destination_longitude BETWEEN -180 AND 180",
            name="ck_orders_destination_longitude",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tracking_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    pickup_address: Mapped[str] = mapped_column(String(500), nullable=False)
    pickup_latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    pickup_longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    destination_address: Mapped[str] = mapped_column(String(500), nullable=False)
    destination_latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    destination_longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    package_description: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    current_status: Mapped[OrderStatus] = mapped_column(
        ORDER_STATUS_DB_TYPE,
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["User"] = relationship(back_populates="orders")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    delivery_proofs: Mapped[list["DeliveryProof"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    review: Mapped["Review | None"] = relationship(back_populates="order", uselist=False)
