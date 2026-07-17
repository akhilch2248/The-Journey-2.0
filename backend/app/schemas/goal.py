from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GoalCreate(BaseModel):
    target_weight_kg: float = Field(gt=0, le=500)
    target_date: Optional[date] = None


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_weight_kg: float
    start_weight_kg: float
    target_date: Optional[date] = None
    active: bool
    created_at: datetime


class GoalProgress(BaseModel):
    goal: GoalRead
    current_weight_kg: Optional[float] = None
    lost_kg: Optional[float] = None
    remaining_kg: Optional[float] = None
    percent_complete: Optional[float] = None
