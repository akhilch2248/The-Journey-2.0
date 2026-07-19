from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import PhysiqueGoal, User
from ..schemas.training import AssessmentSubmit, PhysiqueGoalRead
from ..utils.images import image_abspath, save_image

router = APIRouter(prefix="/physique-goals", tags=["training"])


def _read(goal: PhysiqueGoal) -> PhysiqueGoalRead:
    out = PhysiqueGoalRead.model_validate(goal)
    out.has_image = goal.reference_image_path is not None
    return out


def _active_goal(user: User, db: Session) -> PhysiqueGoal | None:
    return (
        db.query(PhysiqueGoal)
        .filter(PhysiqueGoal.user_id == user.id, PhysiqueGoal.superseded_at.is_(None))
        .order_by(PhysiqueGoal.created_at.desc())
        .first()
    )


@router.post("", response_model=PhysiqueGoalRead, status_code=201)
def create_goal(
    reference_label: str = Form(min_length=1, max_length=120),
    reference_image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set the visual target. Supersedes (never deletes) any previous goal, so
    re-assessment history survives."""
    image_path = save_image(reference_image, f"physique/u{user.id}") if reference_image else None

    db.query(PhysiqueGoal).filter(
        PhysiqueGoal.user_id == user.id, PhysiqueGoal.superseded_at.is_(None)
    ).update({PhysiqueGoal.superseded_at: func.now()})

    goal = PhysiqueGoal(
        user_id=user.id,
        reference_label=reference_label.strip(),
        reference_image_path=image_path,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _read(goal)


@router.get("/active", response_model=PhysiqueGoalRead)
def active_goal(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    goal = _active_goal(user, db)
    if goal is None:
        raise HTTPException(status_code=404, detail="No active physique goal")
    return _read(goal)


@router.post("/{goal_id}/assessment", response_model=PhysiqueGoalRead)
def submit_assessment(
    goal_id: int,
    payload: AssessmentSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Attach the structured gap report (Phase 1 self-report; Phase 2's vision
    assessor writes the same shape)."""
    goal = (
        db.query(PhysiqueGoal)
        .filter(PhysiqueGoal.id == goal_id, PhysiqueGoal.user_id == user.id)
        .first()
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal.gap_report = {
        "emphasis": {k: v for k, v in payload.emphasis.items() if v > 0},
        "notes": payload.notes,
        "source": "self_report",
    }
    db.commit()
    db.refresh(goal)
    return _read(goal)


@router.get("/{goal_id}/image")
def goal_image(goal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    goal = (
        db.query(PhysiqueGoal)
        .filter(PhysiqueGoal.id == goal_id, PhysiqueGoal.user_id == user.id)
        .first()
    )
    if goal is None or not goal.reference_image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_abspath(goal.reference_image_path), media_type="image/jpeg")
