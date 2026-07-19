from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Exercise, PhysiqueGoal, ProgramDay, ProgramExercise, User, WorkoutProgram
from ..schemas.training import GenerateRequest, ProgramRead
from ..services.generator import build_program_spec

router = APIRouter(prefix="/programs", tags=["training"])


def _loaded(q):
    return q.options(
        selectinload(WorkoutProgram.days)
        .selectinload(ProgramDay.exercises)
        .selectinload(ProgramExercise.exercise)
    )


@router.post("/generate", response_model=ProgramRead, status_code=201)
def generate_program(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Build a program from the active goal's gap report. Replaces (archives)
    any currently active program."""
    goal = (
        db.query(PhysiqueGoal)
        .filter(PhysiqueGoal.user_id == user.id, PhysiqueGoal.superseded_at.is_(None))
        .first()
    )
    if goal is None:
        raise HTTPException(status_code=400, detail="Set a physique goal first")
    if not goal.gap_report:
        raise HTTPException(status_code=400, detail="Complete the gap assessment first")

    exercises = db.query(Exercise).all()
    spec = build_program_spec(
        exercises=exercises,
        gap_report=goal.gap_report,
        days_per_week=payload.days_per_week,
        equipment=payload.equipment,
        spine_conscious=payload.spine_conscious,
    )
    if not any(d["exercises"] for d in spec["days"]):
        raise HTTPException(status_code=400, detail="No exercises match that equipment — add more options")

    db.query(WorkoutProgram).filter(
        WorkoutProgram.user_id == user.id, WorkoutProgram.status == "active"
    ).update({WorkoutProgram.status: "archived"})

    program = WorkoutProgram(
        user_id=user.id,
        goal_id=goal.id,
        name=f"{spec['split_name']} — {goal.reference_label}",
        split_type=spec["split_id"],
        days_per_week=payload.days_per_week,
        spine_conscious=payload.spine_conscious,
        equipment=payload.equipment,
        status="active",
    )
    db.add(program)
    db.flush()

    for di, day in enumerate(spec["days"]):
        day_row = ProgramDay(program_id=program.id, day_label=day["label"], order_index=di)
        db.add(day_row)
        db.flush()
        for ei, ex_spec in enumerate(day["exercises"]):
            db.add(ProgramExercise(
                program_day_id=day_row.id,
                exercise_id=ex_spec["exercise"].id,
                order_index=ei,
                target_sets=ex_spec["target_sets"],
                rep_low=ex_spec["rep_low"],
                rep_high=ex_spec["rep_high"],
                target_rir=ex_spec["target_rir"],
                unit=ex_spec["unit"],
            ))
    db.commit()

    return _loaded(db.query(WorkoutProgram)).filter(WorkoutProgram.id == program.id).first()


@router.get("/active", response_model=ProgramRead)
def active_program(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    program = (
        _loaded(db.query(WorkoutProgram))
        .filter(WorkoutProgram.user_id == user.id, WorkoutProgram.status == "active")
        .order_by(WorkoutProgram.created_at.desc())
        .first()
    )
    if program is None:
        raise HTTPException(status_code=404, detail="No active program")
    return program


@router.get("/{program_id}", response_model=ProgramRead)
def get_program(program_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    program = (
        _loaded(db.query(WorkoutProgram))
        .filter(WorkoutProgram.id == program_id, WorkoutProgram.user_id == user.id)
        .first()
    )
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return program
