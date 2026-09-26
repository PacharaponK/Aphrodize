"""Gate public scores using model evidence and calibration provenance.

The decision margin describes certainty of the segmentation output; it is
not a clinical confidence or a calibrated probability of a diagnosis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DEFAULT_POLICY_PATH = Path(__file__).with_name("confidence_policy.json")


@dataclass(frozen=True)
class ConfidencePolicy:
    policy_version: str
    method: str
    status: str
    minimum_confidence: float | None
    calibration_version: str | None
    validation_dataset: str | None
    sample_count: int
    notes: str
    model_architecture: str | None = None
    checkpoint_sha256: str | None = None
    prediction_version: str | None = None
    preprocessing_version: str | None = None
    threshold_version: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "ConfidencePolicy":
        policy = cls(**value)
        policy.validate()
        return policy

    def validate(self) -> None:
        if self.status not in {"calibrated", "not_calibrated"}:
            raise ValueError("confidence policy status must be calibrated or not_calibrated")
        if self.status == "calibrated":
            if self.minimum_confidence is None or not 0 <= self.minimum_confidence <= 1:
                raise ValueError("calibrated policy requires a threshold within [0, 1]")
            if not self.calibration_version or not self.validation_dataset or self.sample_count < 1:
                raise ValueError("calibrated policy requires validation provenance")
            lineage = (
                self.model_architecture,
                self.checkpoint_sha256,
                self.prediction_version,
                self.preprocessing_version,
                self.threshold_version,
            )
            if not all(lineage):
                raise ValueError("calibrated policy requires complete model lineage")

    def compatibility_reasons(self, metadata: dict[str, object]) -> list[str]:
        """Require a calibrated policy to match this exact model and pipeline."""
        if self.status != "calibrated":
            return []
        model = metadata.get("model", {})
        threshold = metadata.get("threshold", {})
        actual = {
            "model_architecture": model.get("architecture"),
            "checkpoint_sha256": model.get("checkpoint_sha256"),
            "prediction_version": metadata.get("prediction_version"),
            "preprocessing_version": metadata.get("preprocessing_version"),
            "threshold_version": threshold.get("version"),
        }
        expected = {name: getattr(self, name) for name in actual}
        return [
            f"policy_{name}_mismatch"
            for name in actual
            if actual[name] != expected[name]
        ]


def load_confidence_policy(path: str | Path = DEFAULT_POLICY_PATH) -> ConfidencePolicy:
    return ConfidencePolicy.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def decision_margin_confidence(probability: np.ndarray, face_mask: np.ndarray) -> float:
    """Average distance from 0.5 over face pixels, scaled to ``[0, 1]``.

    A map near 0.5 has little binary decision margin. Values near 0 or 1
    have more margin; neither case measures clinical correctness.
    """

    if probability.shape != face_mask.shape or probability.ndim != 2:
        raise ValueError("probability and face_mask must be matching 2-D arrays")
    selected = probability[face_mask.astype(bool)]
    if selected.size == 0:
        return 0.0
    if not np.isfinite(selected).all() or np.any((selected < 0) | (selected > 1)):
        raise ValueError("probability values must be finite and within [0, 1]")
    return float(np.mean(np.abs(2.0 * selected.astype(np.float64) - 1.0)))


def evaluate_confidence(
    probability: np.ndarray, face_mask: np.ndarray, policy: ConfidencePolicy
) -> dict[str, object]:
    """Return gate status and reasons for the public AI response.

    The repository's default policy is ``not_calibrated`` and therefore
    withholds approved scores even if the segmentation ran successfully.
    """
    policy.validate()
    value = decision_margin_confidence(probability, face_mask)
    reasons: list[str] = []
    if policy.status != "calibrated":
        reasons.append("confidence_not_calibrated")
    elif value < float(policy.minimum_confidence):
        reasons.append("low_confidence")
    return {
        "value": value,
        "method": policy.method,
        "policy_version": policy.policy_version,
        "calibration_status": policy.status,
        "calibration_version": policy.calibration_version,
        "minimum_confidence": policy.minimum_confidence,
        "validation_dataset": policy.validation_dataset,
        "validation_sample_count": policy.sample_count,
        "passed": not reasons,
        "reasons": reasons,
    }
