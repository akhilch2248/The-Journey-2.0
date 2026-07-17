from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeightCreate(BaseModel):
    date: date
    weight_kg: float = Field(gt=0, le=500)
    source: str = "manual"
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("date")
    @classmethod
    def not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date cannot be in the future")
        return v


class WeightUpdate(BaseModel):
    weight_kg: Optional[float] = Field(default=None, gt=0, le=500)
    note: Optional[str] = Field(default=None, max_length=500)


class WeightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    weight_kg: float
    source: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class WeightStats(BaseModel):
    count: int
    first_date: Optional[date] = None
    latest_date: Optional[date] = None
    start_weight_kg: Optional[float] = None
    latest_weight_kg: Optional[float] = None
    min_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None
    total_change_kg: Optional[float] = None
    moving_avg_7d_kg: Optional[float] = None
    avg_weekly_change_kg: Optional[float] = None
