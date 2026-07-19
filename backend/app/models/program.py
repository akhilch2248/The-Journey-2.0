from sqlalchemy import (
    JSON,
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


class WorkoutProgram(Base):
    __tablename__ = "workout_programs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("physique_goals.id"), nullable=False)
    name = Column(String, nullable=False)
    split_type = Column(String, nullable=False)
    days_per_week = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="active")  # active | archived
    spine_conscious = Column(Boolean, nullable=False, default=True)
    equipment = Column(JSON, nullable=False, default=list)  # what it was generated for
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="programs")
    goal = relationship("PhysiqueGoal")
    days = relationship(
        "ProgramDay",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramDay.order_index",
    )


class ProgramDay(Base):
    __tablename__ = "program_days"

    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey("workout_programs.id"), nullable=False, index=True)
    day_label = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)

    program = relationship("WorkoutProgram", back_populates="days")
    exercises = relationship(
        "ProgramExercise",
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="ProgramExercise.order_index",
    )


class ProgramExercise(Base):
    """One slot in a program day, carrying its own moving targets.

    target_weight_kg starts NULL — the first logged session sets the baseline,
    then the progression engine moves it. consecutive_misses feeds the deload
    rule (2 misses in a row → drop 10%).
    """

    __tablename__ = "program_exercises"

    id = Column(Integer, primary_key=True)
    program_day_id = Column(Integer, ForeignKey("program_days.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    target_sets = Column(Integer, nullable=False)
    rep_low = Column(Integer, nullable=False)
    rep_high = Column(Integer, nullable=False)
    target_rir = Column(Integer, nullable=False)
    unit = Column(String, nullable=False, default="reps")  # reps | seconds
    target_weight_kg = Column(Float, nullable=True)
    consecutive_misses = Column(Integer, nullable=False, default=0)

    day = relationship("ProgramDay", back_populates="exercises")
    exercise = relationship("Exercise")
