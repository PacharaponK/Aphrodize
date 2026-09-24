from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
