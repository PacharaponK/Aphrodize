from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ConsentCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64)


class ConsentRead(BaseModel):
    user_id: UUID
    consent_id: UUID
    version: str
    accepted_at: datetime


class WellnessProfileUpsert(BaseModel):
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
