import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.rider_profile import RiderProfile
    from app.models.user import User


class AssignmentStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        Index(
            "uq_assignments_one_active_per_order",
            "order_id",
            unique=True,
            postgresql_where=text("assignment_status IN ('pending', 'accepted')"),
            sqlite_where=text("assignment_status IN ('pending', 'accepted')"),
        ),
        Index(
            "uq_assignments_one_active_per_rider",
            "rider_id",
            unique=True,
            postgresql_where=text("assignment_status IN ('pending', 'accepted')"),
            sqlite_where=text("assignment_status IN ('pending', 'accepted')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    rider_id: Mapped[int] = mapped_column(
        ForeignKey("rider_profiles.id"), nullable=False, index=True
    )
    dispatcher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        Enum(
            AssignmentStatus,
            name="assignment_status_enum",
            values_callable=lambda members: [member.value for member in members],
        ),
        default=AssignmentStatus.PENDING,
        nullable=False,
    )

    order: Mapped["Order"] = relationship(back_populates="assignments")
    rider: Mapped["RiderProfile"] = relationship(back_populates="assignments")
    dispatcher: Mapped["User"] = relationship()
