from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import ProgramDay, ProgramExercise, SetLog, User, WorkoutProgram, WorkoutSession
from ..schemas.training import (
    ProgressionDecision,
    SessionCompleteRead,
    SessionRead,
    SessionStart,
    SessionStartRead,
    SetCreate,
    SetRead,
    StartSuggestion,
)
from ..services.progression import next_targets
from ..domain import load_progression

router = APIRouter(prefix="/sessions", tags=["training"])


def _own_session(session_id: int, user: User, db: Session) -> WorkoutSession:
    session = (
        db.query(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .filter(WorkoutSession.id == session_id, WorkoutSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=SessionStartRead, status_code=201)
def start_session(
    payload: SessionStart,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    day = (
        db.query(ProgramDay)
        .join(WorkoutProgram)
        .filter(ProgramDay.id == payload.program_day_id, WorkoutProgram.user_id == user.id)
        .first()
    )
    if day is None:
        raise HTTPException(status_code=404, detail="Program day not found")

    open_session = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.user_id == user.id, WorkoutSession.status == "in_progress")
        .first()
    )
    if open_session is not None:
        raise HTTPException(status_code=409, detail=f"Session {open_session.id} is still in progress — complete it first")

    session = WorkoutSession(user_id=user.id, program_day_id=day.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    # Advisory only: flag exercises untouched for 14+ days so the UI can
    # suggest resuming ~10% lighter. Targets themselves don't move on a read.
    rules = load_progression()
    cutoff = datetime.now(timezone.utc) - timedelta(days=rules["stale_days"])
    suggestions = []
    for pe in day.exercises:
        if pe.target_weight_kg is None:
            continue
        last = (
            db.query(SetLog)
            .join(WorkoutSession, SetLog.session_id == WorkoutSession.id)
            .filter(SetLog.program_exercise_id == pe.id, WorkoutSession.status == "completed")
            .order_by(SetLog.id.desc())
            .first()
        )
        if last is None:
            continue
        last_session = db.query(WorkoutSession).filter(WorkoutSession.id == last.session_id).first()
        completed_at = last_session.completed_at
        if completed_at is not None and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        if completed_at is not None and completed_at < cutoff:
            suggestions.append(StartSuggestion(
                program_exercise_id=pe.id,
                suggested_weight_kg=round(pe.target_weight_kg * rules["stale_factor"] * 4) / 4,
                reason=f"More than {rules['stale_days']} days since this exercise — ease back in ~10% lighter",
            ))

    return SessionStartRead(session=SessionRead.model_validate(session), suggestions=suggestions)


@router.get("", response_model=list[SessionRead])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .filter(WorkoutSession.user_id == user.id)
        .order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc())
        .limit(20)
        .all()
    )


@router.get("/{session_id}", response_model=SessionRead)
def get_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _own_session(session_id, user, db)


@router.post("/{session_id}/sets", response_model=SetRead, status_code=201)
def log_set(
    session_id: int,
    payload: SetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _own_session(session_id, user, db)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Session is already completed")

    pe = db.query(ProgramExercise).filter(
        ProgramExercise.id == payload.program_exercise_id,
        ProgramExercise.program_day_id == session.program_day_id,
    ).first()
    if pe is None:
        raise HTTPException(status_code=400, detail="That exercise is not part of this session's day")

    row = SetLog(
        session_id=session.id,
        program_exercise_id=pe.id,
        set_number=payload.set_number,
        weight_kg=payload.weight_kg,
        reps=payload.reps,
        rir=payload.rir,
        is_amrap=payload.is_amrap,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{session_id}/complete", response_model=SessionCompleteRead)
def complete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Close the session and run the progression engine: every exercise that
    got sets logged has its next-session targets recalculated."""
    session = _own_session(session_id, user, db)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Session is already completed")

    sets_by_pe: dict[int, list[SetLog]] = {}
    for s in session.sets:
        sets_by_pe.setdefault(s.program_exercise_id, []).append(s)

    decisions = []
    for pe_id, logs in sets_by_pe.items():
        pe = db.query(ProgramExercise).options(selectinload(ProgramExercise.exercise)).filter(
            ProgramExercise.id == pe_id
        ).first()
        result = next_targets(
            target_weight_kg=pe.target_weight_kg,
            rep_low=pe.rep_low,
            rep_high=pe.rep_high,
            consecutive_misses=pe.consecutive_misses,
            equipment=pe.exercise.equipment,
            category=pe.exercise.category,
            sets=[{"weight_kg": s.weight_kg, "reps": s.reps, "is_amrap": s.is_amrap} for s in logs],
        )
        pe.target_weight_kg = result["next_weight_kg"]
        pe.consecutive_misses = result["consecutive_misses"]
        decisions.append(ProgressionDecision(
            program_exercise_id=pe.id,
            exercise_name=pe.exercise.name,
            decision=result["decision"],
            next_weight_kg=result["next_weight_kg"],
            message=result["message"],
        ))

    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    decisions.sort(key=lambda d: d.program_exercise_id)
    return SessionCompleteRead(session=SessionRead.model_validate(session), decisions=decisions)
