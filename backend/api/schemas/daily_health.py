from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DailyHealthPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    sleep_hours: int = Field(ge=0, le=9)
    sleep_minutes: int = Field(ge=0, le=59)
    water_intake_ml: int = Field(ge=0, le=20_000)
    outdoor_exposure_choice: int = Field(ge=1, le=4)

    @model_validator(mode="after")
    def validate_sleep_duration(self) -> DailyHealthPredictionRequest:
        if self.sleep_hours * 60 + self.sleep_minutes > 540:
            raise ValueError("sleep duration must not exceed 540 minutes")
        return self


class DailyHealthPredictionInput(BaseModel):
    thirst_score_0_10: float | None = Field(default=None, ge=0, le=10)
    dryness_score_0_10: float | None = Field(default=None, ge=0, le=10)
    prediction_status: Literal["predicted", "not_available", "prediction_failed"]
    model_id: str | None = Field(default=None, max_length=128)


class DailyHealthEntryUpsert(BaseModel):
    local_date: date
    timezone: str = Field(default="Asia/Bangkok", min_length=1, max_length=64)
    sleep_duration_minutes: int = Field(ge=0, le=540)
    water_intake_ml: int = Field(ge=0, le=20_000)
    outdoor_exposure_choice: int = Field(ge=1, le=4)
    prediction: DailyHealthPredictionInput | None = None


class DailyHealthProfileUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smoking_status: Literal["never", "former", "current", "prefer_not_to_say"] | None = None


class DailyHealthAgeBandUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_band: Literal["under_13", "13_17", "18_24", "25_34", "35_44", "45_54", "55_plus"]


class DailyHealthMenstrualCheckinUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    currently_menstruating: bool


class DailyHealthOutcomeUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_date: date
    reported_energy_level_0_10: float | None = Field(default=None, ge=0, le=10)
    reported_thirst_level_0_10: float | None = Field(default=None, ge=0, le=10)
    reported_dryness_level_0_10: float | None = Field(default=None, ge=0, le=10)


class DailyHealthEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    local_date: date
    timezone: str
    sleep_duration_minutes: int
    water_intake_ml: int
    outdoor_exposure_choice: int
    sleep_score_0_100: float
    sleep_score_method: str
    predicted_thirst_score_0_10: float | None
    predicted_dryness_score_0_10: float | None
    prediction_target_date: date | None = None
    prediction_status: str
    prediction_model_id: str | None
    data_source: str
    training_eligible: bool
    created_at: datetime
    updated_at: datetime


class DailyHealthProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    smoking_status: str | None
    updated_at: datetime


class DailyHealthAgeBandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    age_band: str
    updated_at: datetime


class DailyHealthMenstrualCheckinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    local_date: date
    currently_menstruating: bool
    created_at: datetime


class DailyHealthOutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    target_date: date
    reported_energy_level_0_10: float | None
    reported_thirst_level_0_10: float | None
    reported_dryness_level_0_10: float | None
    created_at: datetime
    updated_at: datetime
