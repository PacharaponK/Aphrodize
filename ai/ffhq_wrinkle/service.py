"""Application service connecting segmentation, confidence, scoring, and gating."""

from __future__ import annotations

import tempfile
from pathlib import Path
from threading import Lock
from typing import Callable
from uuid import uuid4

import numpy as np
from PIL import Image

from .calibration import load_released_policy_bundle
from .confidence import ConfidencePolicy, evaluate_confidence, load_confidence_policy
from .modeling import ModelBundle, load_wrinkle_model
from .prediction import PredictionResult, ThresholdConfig, predict_image
from .schemas import AnalysisResponse
from .scoring import ScoreConfig, derive_scores

LIMITATIONS = [
    "The research model segments image patterns associated with facial wrinkles.",
    "The score is not clinically validated and must not be interpreted as a diagnosis.",
    "Lighting, pose, focus, cosmetics, occlusion, and camera processing can change the result.",
]


class WrinkleAnalysisService:
    """Run one-image analysis while keeping raw artifacts in temporary storage only."""

    def __init__(
        self,
        *,
        architecture: str = "UNet",
        requested_device: str = "auto",
        confidence_policy: ConfidencePolicy | None = None,
        released_policy_bundle: str | Path | None = None,
        score_config: ScoreConfig = ScoreConfig(),
        recommendation_provider: Callable[[dict[str, object]], list[dict[str, object]]] | None = None,
        predictor: Callable[..., PredictionResult] = predict_image,
        model_loader: Callable[..., ModelBundle] = load_wrinkle_model,
    ) -> None:
        self.architecture = architecture
        self.requested_device = requested_device
        if confidence_policy is not None and released_policy_bundle is not None:
            raise ValueError("provide confidence_policy or released_policy_bundle, not both")
        self.confidence_policy = (
            confidence_policy
            or (
                load_released_policy_bundle(released_policy_bundle)
                if released_policy_bundle is not None
                else load_confidence_policy()
            )
        )
        self.score_config = score_config
        self.recommendation_provider = recommendation_provider or (lambda _score: [])
        self.predictor = predictor
        self.model_loader = model_loader
        self._model_bundle: ModelBundle | None = None
        self._model_lock = Lock()

    def _bundle(self) -> ModelBundle:
        if self._model_bundle is None:
            with self._model_lock:
                if self._model_bundle is None:
                    self._model_bundle = self.model_loader(
                        self.architecture, requested_device=self.requested_device
                    )
        return self._model_bundle

    def analyze_bytes(self, image_bytes: bytes, suffix: str = ".jpg") -> AnalysisResponse:
        """Analyze bytes; temporary source and raw model artifacts are deleted on return."""

        with tempfile.TemporaryDirectory(prefix="aphrodize-wrinkle-") as directory:
            work = Path(directory)
            source = work / f"upload{suffix}"
            source.write_bytes(image_bytes)
            result = self.predictor(
                source,
                work / "prediction",
                architecture=self.architecture,
                requested_device=self.requested_device,
                model_bundle=self._bundle(),
            )
            with Image.open(work / "prediction" / "face_mask.png") as opened:
                face_mask = np.asarray(opened.convert("L")) > 0
            return self.build_response(result, face_mask)

    def build_response(self, result: PredictionResult, face_mask: np.ndarray) -> AnalysisResponse:
        """Build and validate the public response without artifact paths or URLs."""

        metadata = result.metadata
        model = metadata["model"]
        threshold = metadata["threshold"]
        confidence = evaluate_confidence(result.probability, face_mask, self.confidence_policy)
        compatibility_reasons = self.confidence_policy.compatibility_reasons(metadata)
        if compatibility_reasons:
            confidence["passed"] = False
            confidence["reasons"] = [*confidence["reasons"], *compatibility_reasons]
        gate_passed = bool(confidence["passed"])
        reasons = list(confidence["reasons"])
        derived = None
        recommendations: list[dict[str, object]] = []
        if gate_passed:
            derived = derive_scores(
                result.mask, face_mask, gate_passed=True, config=self.score_config
            )
            recommendations = self.recommendation_provider(derived)
        response = {
            "analysis_id": str(uuid4()),
            "status": "completed" if gate_passed else "abstained",
            "model_output": {
                "output_types": ["wrinkle_probability_map", "wrinkle_binary_mask"],
                "architecture": model["architecture"],
                "checkpoint_sha256": model["checkpoint_sha256"],
                "prediction_version": metadata["prediction_version"],
                "preprocessing_version": metadata["preprocessing_version"],
                "threshold_version": threshold["version"],
                "threshold_probability": threshold["probability"],
                "wrinkle_pixels": metadata["wrinkle_pixels"],
                "face_pixels": metadata["face_pixels"],
                "confidence": confidence,
                "artifacts_publicly_available": False,
            },
            "derived_score": derived,
            "recommendation_gate": {
                "eligible": gate_passed,
                "status": "passed" if gate_passed else "withheld",
                "reasons": reasons,
            },
            "recommendations": recommendations,
            "limitations": LIMITATIONS,
        }
        return AnalysisResponse.model_validate(response)
