from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class DeliveryProof(Base):
    __tablename__ = "delivery_proofs"
    __table_args__ = (
        CheckConstraint(
            "verification_attempts >= 0",
            name="ck_delivery_proofs_nonnegative_attempts",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    verification_code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verification_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped["Order"] = relationship(back_populates="delivery_proofs")
