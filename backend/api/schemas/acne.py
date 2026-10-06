from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Region = Literal["forehead", "left_cheek", "right_cheek", "nose", "chin"]


class AcneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    local_date: date
    response: Literal["yes", "no", "unsure"]
    regions: list[Region] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_regions(self):
        if len(set(self.regions)) != len(self.regions):
            raise ValueError("Regions must be unique")
        if self.response != "yes" and self.regions:
            raise ValueError("Regions are only recorded for newly noticed pimples")
        return self


class AcneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    local_date: date
    response: Literal["yes", "no", "unsure"]
    regions: list[Region]
    provenance: str
    consent_version: str
    updated_at: datetime


class AcneConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent_to_store: Literal[True]


class AcneTrainingConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent_to_train_acne: Literal[True]
