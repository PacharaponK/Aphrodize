from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class LifestyleObservationCreate(BaseModel):
    """One standardized daily score and the lifestyle values known for that day."""

    date: date
    wrinkle_score: float = Field(ge=0, le=100)
    sleep_hours: float = Field(ge=0, le=24)
    water_intake_ml: float = Field(ge=0, le=20_000)
    outdoor_minutes: float = Field(ge=0, le=1_440)


class LifestyleObservationRead(LifestyleObservationCreate):
    id: str


class LifestyleForecastRead(BaseModel):
    user_id: str
    report: dict[str, Any]
