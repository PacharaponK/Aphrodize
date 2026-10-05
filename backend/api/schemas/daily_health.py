from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AgeBand = Literal["13_17", "18_60", "61_64", "65_plus"]
SkinType = Literal[
    "normal", "dry", "oily", "combination", "sensitive", "prefer_not_to_say"
]


class DailyHealthPersonalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_given: bool = False
    age_guidance_consent_given: bool = False
    age_band: AgeBand | None = None
    smoking_status: Literal["current", "former", "never", "prefer_not_to_say"] | None = None
    currently_menstruating: bool | None = None
    skin_type_guidance_consent_given: bool = False
    skin_type: SkinType | None = None

    @model_validator(mode="after")
    def require_consent_for_personal_context(self) -> DailyHealthPersonalContext:
        if not self.consent_given and (
            self.smoking_status is not None or self.currently_menstruating is not None
        ):
            raise ValueError("personal context requires explicit consent")
        if not self.age_guidance_consent_given and self.age_band is not None:
            raise ValueError("age band requires separate age-guidance consent")
        if not self.skin_type_guidance_consent_given and self.skin_type is not None:
            raise ValueError("skin type requires separate skin-type guidance consent")
        return self


class DailyHealthPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    sleep_hours: int = Field(ge=0, le=10)
    sleep_minutes: int = Field(ge=0, le=59)
    water_intake_ml: int = Field(ge=0, le=20_000)
    weight_kg: float | None = Field(default=None, ge=1, le=500, allow_inf_nan=False)
    outdoor_exposure_choice: int = Field(ge=1, le=4)
    personal_context: DailyHealthPersonalContext | None = None

    @model_validator(mode="after")
    def validate_sleep_duration(self) -> DailyHealthPredictionRequest:
        if self.sleep_hours * 60 + self.sleep_minutes > 600:
            raise ValueError("sleep duration must not exceed 600 minutes")
        return self


class DailyHealthProfileWeightUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_kg: float = Field(ge=1, le=500, allow_inf_nan=False)
    consent_given: bool

    @model_validator(mode="after")
    def require_weight_profile_consent(self) -> DailyHealthProfileWeightUpsert:
        if not self.consent_given:
            raise ValueError("weight profile requires explicit consent")
        return self


class DailyHealthProfileHeightUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height_cm: float = Field(ge=30, le=300, allow_inf_nan=False)
    consent_given: bool

    @model_validator(mode="after")
    def require_height_profile_consent(self) -> DailyHealthProfileHeightUpsert:
        if not self.consent_given:
            raise ValueError("height profile requires explicit consent")
        return self


class DailyHealthPredictionInput(BaseModel):
    thirst_score_0_10: float | None = Field(default=None, ge=0, le=10)
    dryness_score_0_10: float | None = Field(default=None, ge=0, le=10)
    prediction_status: Literal["predicted", "not_available", "prediction_failed"]
    model_id: str | None = Field(default=None, max_length=128)
    target_date: date | None = None
    forecast_receipt: str | None = Field(default=None, max_length=8192)


class DailyHealthEntryUpsert(BaseModel):
    local_date: date
    timezone: str = Field(default="Asia/Bangkok", min_length=1, max_length=64)
    sleep_duration_minutes: int = Field(ge=0, le=600)
    water_intake_ml: int = Field(ge=0, le=20_000)
    weight_kg: float | None = Field(default=None, ge=1, le=500, allow_inf_nan=False)
    outdoor_exposure_choice: int = Field(ge=1, le=4)
    prediction: DailyHealthPredictionInput | None = None
    personalization_consent: bool = False
    age_guidance_consent: bool = False
    model_training_consent: bool = False
    # Older clients cannot grant the expanded energy scope by sending only True.
    model_training_consent_version: Literal[
        "daily-health-model-training-v1", "daily-health-model-training-v2"
    ] = "daily-health-model-training-v1"
    age_band: AgeBand | None = None
    smoking_status: Literal["current", "former", "never", "prefer_not_to_say"] | None = None
    currently_menstruating: bool | None = None
    skin_type_guidance_consent: bool = False
    skin_type: SkinType | None = None

    @model_validator(mode="after")
    def require_personalization_consent(self) -> DailyHealthEntryUpsert:
        if not self.personalization_consent and (
            self.smoking_status is not None or self.currently_menstruating is not None
        ):
            raise ValueError("personal context requires separate consent")
        if not self.age_guidance_consent and self.age_band is not None:
            raise ValueError("age band requires separate age-guidance consent")
        if not self.skin_type_guidance_consent and self.skin_type is not None:
            raise ValueError("skin type requires separate skin-type guidance consent")
        if self.prediction and self.prediction.target_date is not None:
            if self.prediction.target_date not in (
                self.local_date,
                self.local_date + timedelta(days=1),
            ):
                raise ValueError(
                    "prediction target date must be the input date or the following day"
                )
        return self


class DailyHealthEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    local_date: date
    timezone: str
    sleep_duration_minutes: int
    water_intake_ml: int
    weight_kg: float | None = None
    calculated_thirst_score_0_10: float | None = None
    thirst_score_method: str | None = None
    outdoor_exposure_choice: int
    sleep_score_0_100: float
    sleep_score_method: str
    predicted_thirst_score_0_10: float | None
    predicted_dryness_score_0_10: float | None
    prediction_target_date: date | None
    prediction_status: str
    prediction_model_id: str | None
    next_day_forecasts: dict | None = None
    data_source: str
    training_eligible: bool = False
    created_at: datetime
    updated_at: datetime


class DailyHealthOutcomeUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_date: date
    reported_energy_level_0_10: float | None = Field(default=None, ge=0, le=10)
    reported_thirst_level_0_10: float | None = Field(default=None, ge=0, le=10)
    reported_dryness_level_0_10: float | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def require_an_observed_outcome(self) -> DailyHealthOutcomeUpsert:
        if (
            self.reported_energy_level_0_10 is None
            and self.reported_thirst_level_0_10 is None
            and self.reported_dryness_level_0_10 is None
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
    reported_dryness_level_0_10: float | None
    created_at: datetime
    updated_at: datetime


class DailyHealthModelPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(min_length=1, max_length=128)
    approval_reason: str = Field(min_length=12, max_length=500)

    @field_validator("approval_reason")
    @classmethod
    def require_meaningful_approval_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 12:
            raise ValueError("approval reason must contain at least 12 non-space characters")
        return value


class DailyHealthModelRollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=12, max_length=500)

    @field_validator("reason")
    @classmethod
    def require_meaningful_rollback_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 12:
            raise ValueError("rollback reason must contain at least 12 non-space characters")
        return value


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
