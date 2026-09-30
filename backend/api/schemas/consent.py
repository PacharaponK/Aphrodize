from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ConsentCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64)


class ConsentRead(BaseModel):
    user_id: UUID
    consent_id: UUID
    version: str
    accepted_at: datetime
    access_token: str | None = None


class QuestionnaireCreate(BaseModel):
    answers: dict[str, Any] = Field(
        description="Only user-reported answers; no inferred health data."
    )


class WellnessProfileUpsert(BaseModel):
    """Validated profile fields used by signup and the profile endpoint."""

    sex: Literal["male", "female", "prefer_not_to_say"]
    age_group: Literal["under_13", "13_17", "18_24", "25_34", "35_44", "45_54", "55_plus"]
    guardian_consent: bool = False
    sunscreen_frequency: Literal["never", "sometimes", "most_days", "every_day"]
    skin_type: Literal["dry", "normal", "combination", "oily", "unsure"]
    menstrual_tracking: Literal["yes", "no", "prefer_not_to_say", "not_applicable"]
    wellness_goal: Literal[
        "skin_tracking", "sleep", "hydration", "outdoor_habits", "general_wellness"
    ]
    @model_validator(mode="after")
    def require_guardian_consent_for_children(self) -> "WellnessProfileUpsert":
        if self.age_group == "under_13" and not self.guardian_consent:
            raise ValueError("Guardian consent is required for users under 13")
        return self

    def profile_values(self) -> dict[str, str]:
        values = self.model_dump(exclude={"guardian_consent", "height_cm", "weight_kg"})
        if self.sex == "male":
            values["menstrual_tracking"] = "not_applicable"
        return values


class SafetyScreeningUpdate(BaseModel):
    """The minimum user-reported information required to safely emit product guidance."""

    skin_sensitivity: Literal["low", "medium", "high", "unsure"]
    known_product_allergy: Literal["yes", "no", "unsure"]
    severe_irritation: Literal["yes", "no", "unsure"]
    allergy_details: str | None = Field(default=None, max_length=500)
    # The browser obtains this from GET /questionnaires/initial.  The route also
    # locks the latest row, so a concurrent full edit cannot be overwritten by a
    # safety-only snapshot that was read earlier.
    base_revision_id: UUID

    @model_validator(mode="after")
    def require_allergy_details(self) -> "SafetyScreeningUpdate":
        if self.known_product_allergy == "yes" and not (self.allergy_details or "").strip():
            raise ValueError("Allergy details are required when a product allergy is reported")
        return self

    def safety_answers(self) -> dict[str, str | None]:
        return self.model_dump(exclude={"base_revision_id"}, exclude_none=True)


class InitialWellnessQuestionnaire(BaseModel):
    sex: Literal["male", "female", "prefer_not_to_say"]
    age_group: Literal["under_13", "13_17", "18_24", "25_34", "35_44", "45_54", "55_plus"]
    age_years: int | None = Field(default=None, ge=1, le=120)
    guardian_consent: bool = False
    sleep_hours: float = Field(ge=0, le=24)
    sleep_quality: Literal["poor", "fair", "good", "excellent"]
    water_liters: float = Field(ge=0, le=10)
    outdoor_minutes: int = Field(ge=0, le=1440)
    sunscreen_frequency: Literal["never", "sometimes", "most_days", "every_day"]
    skin_type: Literal["dry", "normal", "combination", "oily", "unsure"]
    skin_sensitivity: Literal["low", "medium", "high", "unsure"] = "unsure"
    known_product_allergy: Literal["yes", "no", "unsure"] = "unsure"
    allergy_details: str | None = Field(default=None, max_length=500)
    severe_irritation: Literal["yes", "no", "unsure"] = "unsure"
    stress_level: int = Field(ge=1, le=5)
    menstrual_tracking: Literal["yes", "no", "prefer_not_to_say", "not_applicable"]
    menstrual_status: Literal[
        "on_period", "not_on_period", "unsure", "prefer_not_to_say", "not_applicable"
    ]
    wellness_goal: Literal[
        "skin_tracking", "sleep", "hydration", "outdoor_habits", "general_wellness"
    ]
    height_cm: float | None = Field(default=None, ge=30, le=300, allow_inf_nan=False)
    weight_kg: float | None = Field(default=None, ge=1, le=500, allow_inf_nan=False)
    # Required only for a full revision. Initial creation has no base revision.
    base_revision_id: UUID | None = None

    @model_validator(mode="after")
    def require_guardian_consent_for_children(self) -> "InitialWellnessQuestionnaire":
        if self.age_group == "under_13" and not self.guardian_consent:
            raise ValueError("Guardian consent is required for users under 13")
        if self.age_years is not None:
            expected_group = (
                "under_13" if self.age_years < 13 else "13_17" if self.age_years < 18
                else "18_24" if self.age_years < 25 else "25_34" if self.age_years < 35
                else "35_44" if self.age_years < 45 else "45_54" if self.age_years < 55
                else "55_plus"
            )
            if self.age_group != expected_group:
                raise ValueError("age_group must match age_years")
        if self.known_product_allergy == "yes" and not (self.allergy_details or "").strip():
            raise ValueError("Allergy details are required when a product allergy is reported")
        return self

    def answers_for_storage(self) -> dict[str, Any]:
        answers = self.model_dump(exclude={"base_revision_id"})
        if self.sex == "male":
            answers["menstrual_tracking"] = "not_applicable"
            answers["menstrual_status"] = "not_applicable"
        return answers
