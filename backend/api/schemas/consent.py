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
        values = self.model_dump(exclude={"guardian_consent"})
        if self.sex == "male":
            values["menstrual_tracking"] = "not_applicable"
        return values


class SafetyScreeningUpdate(BaseModel):
    """The minimum user-reported information required to safely emit product guidance."""

    skin_sensitivity: Literal["low", "medium", "high", "unsure"]
    known_product_allergy: Literal["yes", "no", "unsure"]
    severe_irritation: Literal["yes", "no", "unsure"]
    # The browser obtains this from GET /questionnaires/initial.  The route also
    # locks the latest row, so a concurrent full edit cannot be overwritten by a
    # safety-only snapshot that was read earlier.
    base_revision_id: UUID

    def safety_answers(self) -> dict[str, str]:
        return self.model_dump(exclude={"base_revision_id"})


class InitialWellnessQuestionnaire(BaseModel):
    sex: Literal["male", "female", "prefer_not_to_say"]
    age_group: Literal["under_13", "13_17", "18_24", "25_34", "35_44", "45_54", "55_plus"]
    guardian_consent: bool = False
    sleep_hours: float = Field(ge=0, le=24)
    sleep_quality: Literal["poor", "fair", "good", "excellent"]
    water_liters: float = Field(ge=0, le=10)
    outdoor_minutes: int = Field(ge=0, le=1440)
    sunscreen_frequency: Literal["never", "sometimes", "most_days", "every_day"]
    skin_type: Literal["dry", "normal", "combination", "oily", "unsure"]
    skin_sensitivity: Literal["low", "medium", "high", "unsure"] = "unsure"
    known_product_allergy: Literal["yes", "no", "unsure"] = "unsure"
    severe_irritation: Literal["yes", "no", "unsure"] = "unsure"
    stress_level: int = Field(ge=1, le=5)
    menstrual_tracking: Literal["yes", "no", "prefer_not_to_say", "not_applicable"]
    menstrual_status: Literal[
        "on_period", "not_on_period", "unsure", "prefer_not_to_say", "not_applicable"
    ]
    wellness_goal: Literal["skin_tracking", "sleep", "hydration", "outdoor_habits", "general_wellness"]
    # Required only for a full revision. Initial creation has no base revision.
    base_revision_id: UUID | None = None

    @model_validator(mode="after")
    def require_guardian_consent_for_children(self) -> "InitialWellnessQuestionnaire":
        if self.age_group == "under_13" and not self.guardian_consent:
            raise ValueError("Guardian consent is required for users under 13")
        return self

    def answers_for_storage(self) -> dict[str, Any]:
        answers = self.model_dump(exclude={"base_revision_id"})
        if self.sex == "male":
            answers["menstrual_tracking"] = "not_applicable"
            answers["menstrual_status"] = "not_applicable"
        return answers
