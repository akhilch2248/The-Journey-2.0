from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..domain import REGION_MUSCLES

EQUIPMENT_CHOICES = {"barbell", "dumbbell", "cable", "machine", "bodyweight", "kettlebell", "band"}


# ---------- exercises ----------

class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    primary_muscle: str
    secondary_muscles: list[str]
    equipment: str
    movement_pattern: str
    category: str
    contraindications: list[str]
    cue: str


# ---------- physique goals ----------

class AssessmentSubmit(BaseModel):
    """The structured self-report gap form (Phase 1's Option B).

    emphasis maps region → priority 0-3 (0 = skip). The vision assessor
    (Phase 2) will produce this same shape.
    """

    emphasis: dict[str, int]
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("emphasis")
    @classmethod
    def check_regions(cls, v: dict[str, int]) -> dict[str, int]:
        unknown = set(v) - set(REGION_MUSCLES)
        if unknown:
            raise ValueError(f"Unknown regions: {sorted(unknown)}. Valid: {sorted(REGION_MUSCLES)}")
        for region, priority in v.items():
            if not isinstance(priority, int) or not 0 <= priority <= 3:
                raise ValueError(f"Priority for {region} must be an integer 0-3")
        if not any(p > 0 for p in v.values()):
            raise ValueError("Set at least one region to priority 1-3")
        return v


class PhysiqueGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_label: str
    gap_report: dict | None
    created_at: datetime
    superseded_at: datetime | None
    has_image: bool = False


# ---------- programs ----------

class GenerateRequest(BaseModel):
    days_per_week: int = Field(ge=2, le=6)
    equipment: list[str] = Field(min_length=1)
    spine_conscious: bool = True

    @field_validator("equipment")
    @classmethod
    def check_equipment(cls, v: list[str]) -> list[str]:
        unknown = set(v) - EQUIPMENT_CHOICES
        if unknown:
            raise ValueError(f"Unknown equipment: {sorted(unknown)}. Valid: {sorted(EQUIPMENT_CHOICES)}")
        return sorted(set(v))


class ProgramExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_index: int
    target_sets: int
    rep_low: int
    rep_high: int
    target_rir: int
    unit: str
    target_weight_kg: float | None
    consecutive_misses: int
    exercise: ExerciseRead


class ProgramDayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day_label: str
    order_index: int
    exercises: list[ProgramExerciseRead]


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal_id: int
    name: str
    split_type: str
    days_per_week: int
    status: str
    spine_conscious: bool
    equipment: list[str]
    created_at: datetime
    days: list[ProgramDayRead]


# ---------- sessions ----------

class SessionStart(BaseModel):
    program_day_id: int


class SetCreate(BaseModel):
    program_exercise_id: int
    set_number: int = Field(ge=1, le=20)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    reps: int = Field(ge=0, le=600)  # seconds for conditioning work
    rir: int | None = Field(default=None, ge=0, le=5)
    is_amrap: bool = False


class SetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_exercise_id: int
    set_number: int
    weight_kg: float | None
    reps: int
    rir: int | None
    is_amrap: bool


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_day_id: int
    started_at: datetime
    completed_at: datetime | None
    status: str
    sets: list[SetRead]


class StartSuggestion(BaseModel):
    program_exercise_id: int
    suggested_weight_kg: float
    reason: str


class SessionStartRead(BaseModel):
    session: SessionRead
    suggestions: list[StartSuggestion]


class ProgressionDecision(BaseModel):
    program_exercise_id: int
    exercise_name: str
    decision: str  # baseline | increase | add_rep | hold | deload
    next_weight_kg: float | None
    message: str


class SessionCompleteRead(BaseModel):
    session: SessionRead
    decisions: list[ProgressionDecision]


# ---------- progress photos ----------

class ProgressPhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    taken_at: date
    note: str | None
    created_at: datetime
