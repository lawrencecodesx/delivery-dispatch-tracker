from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.order import ORDER_STATUS_DB_TYPE, OrderStatus

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    previous_status: Mapped[OrderStatus | None] = mapped_column(ORDER_STATUS_DB_TYPE)
    new_status: Mapped[OrderStatus] = mapped_column(ORDER_STATUS_DB_TYPE, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped["Order"] = relationship(back_populates="status_history")
    actor: Mapped["User"] = relationship()
