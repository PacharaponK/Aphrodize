"""Public API schemas for Phase 6 wrinkle analysis."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfidenceResult(StrictModel):
    value: float = Field(ge=0, le=1)
    method: str
    policy_version: str
    calibration_status: Literal["calibrated", "not_calibrated"]
    calibration_version: str | None
    minimum_confidence: float | None
    validation_dataset: str | None
    validation_sample_count: int = Field(ge=0)
    passed: bool
    reasons: list[str]


class ResearchModelOutput(StrictModel):
    output_types: list[Literal["wrinkle_probability_map", "wrinkle_binary_mask"]]
    architecture: str
    checkpoint_sha256: str
    prediction_version: str
    preprocessing_version: str
    threshold_version: str
    threshold_probability: float = Field(ge=0, le=1)
    wrinkle_pixels: int = Field(ge=0)
    face_pixels: int = Field(ge=0)
    confidence: ConfidenceResult
    artifacts_publicly_available: Literal[False] = False


class AreaScore(StrictModel):
    score: float = Field(ge=0, le=100)
    severity_label: Literal[
        "no_segmented_area",
        "low_visible_area",
        "medium_visible_area",
        "high_visible_area",
    ]
    wrinkle_area_ratio: float = Field(ge=0, le=1)
    wrinkle_pixels: int = Field(ge=0)
    evaluated_pixels: int = Field(ge=0)
    score_version: str
    roi_version: str


class DerivedScore(StrictModel):
    score_version: str
    roi_version: str
    formula: str
    overall: AreaScore
    regions: dict[str, AreaScore]
    disclaimer: str


class RecommendationGate(StrictModel):
    eligible: bool
    status: Literal["passed", "withheld"]
    reasons: list[str]


class AnalysisResponse(StrictModel):
    analysis_id: str
    status: Literal["completed", "abstained"]
    model_output: ResearchModelOutput
    derived_score: DerivedScore | None
    recommendation_gate: RecommendationGate
    recommendations: list[dict[str, Any]]
    limitations: list[str]


class QualityRejection(StrictModel):
    status: Literal["rejected"] = "rejected"
    code: Literal["quality_gate_rejected"] = "quality_gate_rejected"
    quality_flags: list[str]
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
