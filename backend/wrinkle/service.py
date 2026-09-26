"""Turn one image into a public AI response without retaining raw arrays.

``analyze_bytes`` owns the temporary source/prediction files, while
``predict_image`` performs preprocessing and segmentation. ``build_response``
then applies the confidence policy before exposing scores or recommendations.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from uuid import uuid4

import numpy as np
from PIL import Image

from ai.ffhq_wrinkle.calibration import load_released_policy_bundle
from ai.ffhq_wrinkle.confidence import (
    ConfidencePolicy,
    evaluate_confidence,
    load_confidence_policy,
)
from ai.ffhq_wrinkle.modeling import ModelBundle, load_wrinkle_model
from ai.ffhq_wrinkle.prediction import PredictionResult, predict_image
from ai.ffhq_wrinkle.scoring import ScoreConfig, derive_scores

from .schemas import AnalysisResponse

LIMITATIONS = [
    "The research model segments image patterns associated with facial wrinkles.",
    "The score is not clinically validated and must not be interpreted as a diagnosis.",
    "Lighting, pose, focus, cosmetics, occlusion, and camera processing can change the result.",
]


class WrinkleAnalysisService:
    """Orchestrate one-image inference and keep the Stage-2 model cached."""

    def __init__(
        self,
        *,
        architecture: str = "UNet",
        requested_device: str = "auto",
        confidence_policy: ConfidencePolicy | None = None,
        released_policy_bundle: str | Path | None = None,
        score_config: ScoreConfig = ScoreConfig(),
        recommendation_provider: Callable[[dict[str, object]], list[dict[str, object]]]
        | None = None,
        predictor: Callable[..., PredictionResult] = predict_image,
        model_loader: Callable[..., ModelBundle] = load_wrinkle_model,
    ) -> None:
        self.architecture = architecture
        self.requested_device = requested_device
        if confidence_policy is not None and released_policy_bundle is not None:
            raise ValueError("provide confidence_policy or released_policy_bundle, not both")
        self.confidence_policy = confidence_policy or (
            load_released_policy_bundle(released_policy_bundle)
            if released_policy_bundle is not None
            else load_confidence_policy()
        )
        self.score_config = score_config
        self.recommendation_provider = recommendation_provider or (lambda _score: [])
        self.predictor = predictor
        self.model_loader = model_loader
        self._model_bundle: ModelBundle | None = None
        self._model_lock = Lock()

    def _bundle(self) -> ModelBundle:
        """Load the verified checkpoint once, even with concurrent requests."""
        if self._model_bundle is None:
            with self._model_lock:
                if self._model_bundle is None:
                    self._model_bundle = self.model_loader(
                        self.architecture, requested_device=self.requested_device
                    )
        return self._model_bundle

    def analyze_bytes(
        self,
        image_bytes: bytes,
        suffix: str = ".jpg",
        *,
        artifact_sink: Callable[[dict[str, bytes]], None] | None = None,
    ) -> AnalysisResponse:
        """Analyze image bytes and delete local artifacts on return or error.

        ``artifact_sink`` can copy the overlay and wrinkle-mask PNG bytes to
        the caller before cleanup. It never receives logits or probabilities.
        """

        with tempfile.TemporaryDirectory(prefix="aphrodize-wrinkle-") as directory:
            work = Path(directory)
            source = work / f"upload{suffix}"
            source.write_bytes(image_bytes)
            # Resolve the verified model before prediction; later requests reuse the cached bundle.
            result = self.predictor(
                source,
                work / "prediction",
                architecture=self.architecture,
                requested_device=self.requested_device,
                model_bundle=self._bundle(),
            )
            # Scoring needs the same skin/nose area that preprocessing used.
            with Image.open(work / "prediction" / "face_mask.png") as opened:
                face_mask = np.asarray(opened.convert("L")) > 0
            if artifact_sink is not None:
                # Copy only display images before the temporary directory is removed.
                artifact_sink({
                    "overlay": (work / "prediction" / "overlay.png").read_bytes(),
                    "mask": (work / "prediction" / "wrinkle_mask.png").read_bytes(),
                })
            return self.build_response(result, face_mask)

    def build_response(self, result: PredictionResult, face_mask: np.ndarray) -> AnalysisResponse:
        """Convert raw arrays into a policy-gated, path-free public response.

        A failed confidence gate still produces an explicitly experimental
        score, but withholds the derived score and recommendations.
        """

        metadata = result.metadata
        model = metadata["model"]
        threshold = metadata["threshold"]
        confidence = evaluate_confidence(result.probability, face_mask, self.confidence_policy)
        # A calibrated policy is valid only for the exact model and pipeline versions.
        compatibility_reasons = self.confidence_policy.compatibility_reasons(metadata)
        if compatibility_reasons:
            confidence["passed"] = False
            confidence["reasons"] = [*confidence["reasons"], *compatibility_reasons]
        gate_passed = bool(confidence["passed"])
        reasons = list(confidence["reasons"])
        derived = None
        experimental = None
        recommendations: list[dict[str, object]] = []
        if gate_passed:
            derived = derive_scores(
                result.mask, face_mask, gate_passed=True, config=self.score_config
            )
            recommendations = self.recommendation_provider(derived)
        else:
            experimental = derive_scores(
                result.mask,
                face_mask,
                gate_passed=False,
                allow_experimental=True,
                config=self.score_config,
            )
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
            "experimental_score": experimental,
            "recommendation_gate": {
                "eligible": gate_passed,
                "status": "passed" if gate_passed else "withheld",
                "reasons": reasons,
            },
            "recommendations": recommendations,
            "limitations": LIMITATIONS,
        }
        return AnalysisResponse.model_validate(response)
