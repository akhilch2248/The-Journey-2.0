from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from ..database import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    program_day_id = Column(Integer, ForeignKey("program_days.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress | completed

    user = relationship("User", back_populates="workout_sessions")
    day = relationship("ProgramDay")
    sets = relationship(
        "SetLog",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SetLog.id",
    )


class SetLog(Base):
    """One logged set — the row the progression engine reads.

    weight_kg is NULL for bodyweight work; reps holds seconds when the parent
    ProgramExercise.unit is "seconds" (conditioning intervals).
    """

    __tablename__ = "set_logs"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False, index=True)
    program_exercise_id = Column(Integer, ForeignKey("program_exercises.id"), nullable=False, index=True)
    set_number = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=True)
    reps = Column(Integer, nullable=False)
    rir = Column(Integer, nullable=True)
    is_amrap = Column(Boolean, nullable=False, default=False)

    session = relationship("WorkoutSession", back_populates="sets")
    program_exercise = relationship("ProgramExercise")
