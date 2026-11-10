import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.rider_location import RiderLocation
    from app.models.user import User


class RiderAvailability(str, enum.Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ON_DELIVERY = "on_delivery"


class RiderProfile(Base):
    __tablename__ = "rider_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_registration: Mapped[str] = mapped_column(String(30), nullable=False)
    availability_status: Mapped[RiderAvailability] = mapped_column(
        Enum(
            RiderAvailability,
            name="rider_availability_enum",
            values_callable=lambda members: [member.value for member in members],
        ),
        default=RiderAvailability.UNAVAILABLE,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="rider_profile")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="rider")
    locations: Mapped[list["RiderLocation"]] = relationship(
        back_populates="rider", cascade="all, delete-orphan"
    )
