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
    stress_level: int = Field(ge=1, le=5)
    menstrual_tracking: Literal["yes", "no", "prefer_not_to_say", "not_applicable"]
    menstrual_status: Literal[
        "on_period", "not_on_period", "unsure", "prefer_not_to_say", "not_applicable"
    ]
    wellness_goal: Literal["skin_tracking", "sleep", "hydration", "outdoor_habits", "general_wellness"]

    @model_validator(mode="after")
    def require_guardian_consent_for_children(self) -> "InitialWellnessQuestionnaire":
        if self.age_group == "under_13" and not self.guardian_consent:
            raise ValueError("Guardian consent is required for users under 13")
        return self

    def answers_for_storage(self) -> dict[str, Any]:
        answers = self.model_dump()
        if self.sex == "male":
            answers["menstrual_tracking"] = "not_applicable"
            answers["menstrual_status"] = "not_applicable"
        return answers
