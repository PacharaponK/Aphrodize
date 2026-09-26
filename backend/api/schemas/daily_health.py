from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AgeBand = Literal["13_17", "18_60", "61_64", "65_plus"]


class DailyHealthPersonalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_given: bool = False
    age_guidance_consent_given: bool = False
    age_band: AgeBand | None = None
    smoking_status: Literal["current", "former", "never", "prefer_not_to_say"] | None = None
    currently_menstruating: bool | None = None

    @model_validator(mode="after")
    def require_consent_for_personal_context(self) -> DailyHealthPersonalContext:
        if not self.consent_given and (
            self.smoking_status is not None
            or self.currently_menstruating is not None
        ):
            raise ValueError("personal context requires explicit consent")
        if not self.age_guidance_consent_given and self.age_band is not None:
            raise ValueError("age band requires separate age-guidance consent")
        return self


class DailyHealthPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    sleep_hours: int = Field(ge=0, le=9)
    sleep_minutes: int = Field(ge=0, le=59)
    water_intake_ml: int = Field(ge=0, le=20_000)
    outdoor_exposure_choice: int = Field(ge=1, le=4)
    personal_context: DailyHealthPersonalContext | None = None

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
    personalization_consent: bool = False
    age_guidance_consent: bool = False
    age_band: AgeBand | None = None
    smoking_status: Literal["current", "former", "never", "prefer_not_to_say"] | None = None
    currently_menstruating: bool | None = None

    @model_validator(mode="after")
    def require_personalization_consent(self) -> DailyHealthEntryUpsert:
        if not self.personalization_consent and (
            self.smoking_status is not None
            or self.currently_menstruating is not None
        ):
            raise ValueError("personal context requires separate consent")
        if not self.age_guidance_consent and self.age_band is not None:
            raise ValueError("age band requires separate age-guidance consent")
        return self


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
    prediction_status: str
    prediction_model_id: str | None
    data_source: str
    training_eligible: bool
    created_at: datetime
    updated_at: datetime


class DailyHealthOutcomeUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_date: date
    reported_energy_level_0_10: float | None = Field(default=None, ge=0, le=10)
    reported_thirst_level_0_10: float | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def require_an_observed_outcome(self) -> DailyHealthOutcomeUpsert:
        if (
            self.reported_energy_level_0_10 is None
            and self.reported_thirst_level_0_10 is None
        ):
            raise ValueError("at least one user-reported outcome is required")
        return self


class DailyHealthOutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    target_date: date
    reported_energy_level_0_10: float | None
    reported_thirst_level_0_10: float | None
    created_at: datetime
    updated_at: datetime
