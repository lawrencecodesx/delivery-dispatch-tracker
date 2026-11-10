from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.rider_profile import RiderProfile


class RiderLocation(Base):
    __tablename__ = "rider_locations"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_rider_locations_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_rider_locations_longitude"),
        CheckConstraint("accuracy IS NULL OR accuracy >= 0", name="ck_rider_locations_accuracy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rider_id: Mapped[int] = mapped_column(
        ForeignKey("rider_profiles.id"), nullable=False, index=True
    )
    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "assignments.id",
            name="fk_rider_locations_assignment_id_assignments",
            ondelete="SET NULL",
        ),
        index=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    accuracy: Mapped[float | None] = mapped_column(Float)

    rider: Mapped["RiderProfile"] = relationship(back_populates="locations")
    assignment: Mapped["Assignment | None"] = relationship()
