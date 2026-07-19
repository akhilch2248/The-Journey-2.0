from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Exercise, User
from ..schemas.training import ExerciseRead

router = APIRouter(prefix="/exercises", tags=["training"])


@router.get("", response_model=list[ExerciseRead])
def list_exercises(
    muscle: str | None = None,
    equipment: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Exercise)
    if muscle:
        q = q.filter(Exercise.primary_muscle == muscle)
    if equipment:
        q = q.filter(Exercise.equipment == equipment)
    return q.order_by(Exercise.primary_muscle, Exercise.name).all()
