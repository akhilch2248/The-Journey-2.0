from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models.goal import Goal
from ..models.user import User
from ..models.weight import WeightLog
from ..schemas.goal import GoalCreate, GoalProgress, GoalRead

router = APIRouter(prefix="/goals", tags=["goals"])


def _latest_weight(user: User, db: Session) -> WeightLog | None:
    return (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.date.desc())
        .first()
    )


@router.put("", response_model=GoalRead)
def set_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set the active goal. Replaces any previous active goal; the starting
    weight is snapshotted from the latest logged weight."""
    latest = _latest_weight(user, db)
    if latest is None:
        raise HTTPException(status_code=400, detail="Log at least one weight before setting a goal")

    db.query(Goal).filter(Goal.user_id == user.id, Goal.active.is_(True)).update(
        {Goal.active: False}
    )
    goal = Goal(
        user_id=user.id,
        target_weight_kg=payload.target_weight_kg,
        start_weight_kg=latest.weight_kg,
        target_date=payload.target_date,
        active=True,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/current", response_model=GoalProgress)
def current_goal(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    goal = (
        db.query(Goal)
        .filter(Goal.user_id == user.id, Goal.active.is_(True))
        .order_by(Goal.created_at.desc())
        .first()
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="No active goal")

    latest = _latest_weight(user, db)
    current = latest.weight_kg if latest else None

    lost = remaining = percent = None
    if current is not None:
        lost = round(goal.start_weight_kg - current, 2)
        remaining = round(current - goal.target_weight_kg, 2)
        planned = goal.start_weight_kg - goal.target_weight_kg
        if planned != 0:
            percent = round(max(0.0, min(100.0, lost / planned * 100)), 1)
        else:
            percent = 100.0

    return GoalProgress(
        goal=goal,
        current_weight_kg=current,
        lost_kg=lost,
        remaining_kg=remaining,
        percent_complete=percent,
    )
