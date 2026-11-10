from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.authentication import get_current_user
from app.models.assignment import Assignment, AssignmentStatus
from app.models.order import Order
from app.models.rider_location import RiderLocation
from app.models.rider_profile import RiderProfile
from app.models.user import User, UserRole
from app.schemas.rider import RiderLocationResponse
from app.schemas.tracking import TrackingLocationResponse

router = APIRouter(prefix="/api/v1/tracking", tags=["tracking"])
ACTIVE_ASSIGNMENTS = {AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED}


def _authorized_tracking_order(
    db: Session, order_id: int, user: User
) -> tuple[Order, Assignment]:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == UserRole.CUSTOMER:
        if order.customer_id != user.id:
            raise HTTPException(status_code=404, detail="Order not found")
    elif user.role == UserRole.RIDER:
        profile = db.scalar(select(RiderProfile).where(RiderProfile.user_id == user.id))
        if profile is None:
            raise HTTPException(status_code=404, detail="Order not found")
        assignment = db.scalar(
            select(Assignment.id).where(
                Assignment.order_id == order.id,
                Assignment.rider_id == profile.id,
                Assignment.assignment_status.in_(ACTIVE_ASSIGNMENTS),
            )
        )
        if assignment is None:
            raise HTTPException(status_code=404, detail="Order not found")
    elif user.role not in {UserRole.ADMIN, UserRole.DISPATCHER}:
        raise HTTPException(status_code=403, detail="You cannot access tracking data")

    assignment = db.scalar(
        select(Assignment)
        .where(
            Assignment.order_id == order.id,
            Assignment.assignment_status.in_(ACTIVE_ASSIGNMENTS),
        )
        .order_by(Assignment.assigned_at.desc())
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="No active rider assignment exists")
    return order, assignment


@router.get("/{order_id}", response_model=TrackingLocationResponse)
def get_latest_location(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TrackingLocationResponse:
    order, assignment = _authorized_tracking_order(db, order_id, user)
    location = db.scalar(
        select(RiderLocation)
        .where(RiderLocation.assignment_id == assignment.id)
        .order_by(RiderLocation.recorded_at.desc())
        .limit(1)
    )
    if location is None:
        raise HTTPException(status_code=404, detail="No rider location has been reported")
    return TrackingLocationResponse(
        order_id=order.id,
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy=location.accuracy,
        recorded_at=location.recorded_at,
    )


@router.get("/{order_id}/history", response_model=list[RiderLocationResponse])
def get_location_history(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[RiderLocation]:
    _, assignment = _authorized_tracking_order(db, order_id, user)
    return list(
        db.scalars(
            select(RiderLocation)
            .where(RiderLocation.assignment_id == assignment.id)
            .order_by(RiderLocation.recorded_at.desc())
            .limit(limit)
        ).all()
    )