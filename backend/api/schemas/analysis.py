from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisRead(BaseModel):
    id: UUID
    status: str
    model_family: str
    model_version: str
    image_quality_score: float | None
    quality_flags: list[str]
    result: dict[str, Any] | None
    error_category: str | None
    created_at: datetime


class TrainingRequest(BaseModel):
    model_family: Literal["time_series", "tabular", "image_segmentation"]
    dataset_uri: str = Field(min_length=3, max_length=512)
    config: dict[str, Any] = Field(default_factory=dict)


class TrainingRunRead(BaseModel):
    id: UUID
    model_family: str
    dataset_uri: str
    status: str
    mlflow_run_id: str | None
    created_at: datetime


class InferenceRequest(BaseModel):
    model_family: Literal["time_series", "tabular"]
    model_uri: str = Field(min_length=3, max_length=512, description="Approved MLflow model URI.")
    input_data: dict[str, Any] = Field(default_factory=dict)


class InferenceRunRead(BaseModel):
    id: UUID
    model_family: str
    model_uri: str
    status: str
    result: dict[str, Any] | None
    error_category: str | None
    created_at: datetime
