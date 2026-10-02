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

from .approved_model import approved_checkpoint
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
        approved_model_manifest: str | Path | None = None,
    ) -> None:
        # Defaults select the published UNet checkpoint and the available device.
        self.architecture = architecture
        self.requested_device = requested_device
        # Callers must choose one source of confidence policy settings.
        if confidence_policy is not None and released_policy_bundle is not None:
            raise ValueError("provide confidence_policy or released_policy_bundle, not both")
        # Without a released policy, the default policy marks confidence uncalibrated.
        self.confidence_policy = confidence_policy or (
            load_released_policy_bundle(released_policy_bundle)
            if released_policy_bundle is not None
            else load_confidence_policy()
        )
        # Keep scoring, recommendation, and model functions replaceable for callers/tests.
        self.score_config = score_config
        self.recommendation_provider = recommendation_provider or (lambda _score: [])
        self.predictor = predictor
        self.model_loader = model_loader
        self.approved_model_manifest = approved_model_manifest
        # The expensive Stage-2 checkpoint is cached for this worker process.
        self._model_bundle: ModelBundle | None = None
        # Concurrent requests must not both load the same large checkpoint.
        self._model_lock = Lock()

    def _bundle(self) -> ModelBundle:
        """Load the verified checkpoint once, even with concurrent requests."""
        # Fast path: reuse a model that an earlier image already loaded.
        if self._model_bundle is None:
            with self._model_lock:
                # Recheck after taking the lock in case another caller loaded it.
                if self._model_bundle is None:
                    if self.approved_model_manifest:
                        # The manifest gate verifies human approval and checkpoint bytes.
                        checkpoint = approved_checkpoint(self.approved_model_manifest)
                        self._model_bundle = self.model_loader(
                            self.architecture,
                            checkpoint_path=checkpoint,
                            requested_device=self.requested_device,
                            verify_official=False,
                        )
                    else:
                        # Without a selected candidate, load the verified default model.
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

        ``artifact_sink`` can copy display PNGs and the aligned review image
        to the caller before cleanup. It never receives logits or probabilities.
        """

        # Everything here is local scratch space deleted when this block ends.
        with tempfile.TemporaryDirectory(prefix="aphrodize-wrinkle-") as directory:
            work = Path(directory)
            # Reconstruct an image file because the preprocessing code takes a path.
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
            # The predictor returned the wrinkle mask but not its face mask;
            # read the latter from the PNG saved by preprocess_image().
            with Image.open(work / "prediction" / "face_mask.png") as opened:
                face_mask = np.asarray(opened.convert("L")) > 0
            if artifact_sink is not None:
                # Copy display PNGs and the aligned review face before scratch cleanup.
                artifact_sink({
                    "overlay": (work / "prediction" / "overlay.png").read_bytes(),
                    "mask": (work / "prediction" / "wrinkle_mask.png").read_bytes(),
                    "aligned_face": (work / "prediction" / "aligned_face.png").read_bytes(),
                })
            # Convert arrays to a small JSON-compatible response before cleanup.
            return self.build_response(result, face_mask)

    def build_response(self, result: PredictionResult, face_mask: np.ndarray) -> AnalysisResponse:
        """Convert raw arrays into a policy-gated, path-free public response.

        A failed confidence gate still produces an explicitly experimental
        score, but withholds the derived score and recommendations.
        """

        # Metadata identifies the exact model, threshold, and pipeline versions.
        metadata = result.metadata
        model = metadata["model"]
        threshold = metadata["threshold"]
        # Decision margin measures distance from a 50/50 pixel prediction.
        # It is not the probability that the score is medically correct.
        confidence = evaluate_confidence(result.probability, face_mask, self.confidence_policy)
        # A released policy is valid only for the exact model and pipeline versions.
        compatibility_reasons = self.confidence_policy.compatibility_reasons(metadata)
        if compatibility_reasons:
            # A mismatched model or preprocessing version withholds released scores.
            confidence["passed"] = False
            confidence["reasons"] = [*confidence["reasons"], *compatibility_reasons]
        # Both measured confidence and policy/model compatibility must pass.
        gate_passed = bool(confidence["passed"])
        reasons = list(confidence["reasons"])
        # Only one of these score fields is populated for a given response.
        derived = None
        experimental = None
        recommendations: list[dict[str, object]] = []
        if gate_passed:
            # Approved scores can be used by the recommendation provider.
            derived = derive_scores(
                result.mask, face_mask, gate_passed=True, config=self.score_config
            )
            recommendations = self.recommendation_provider(derived)
        else:
            # Still show the area calculation, clearly marked experimental.
            experimental = derive_scores(
                result.mask,
                face_mask,
                gate_passed=False,
                allow_experimental=True,
                config=self.score_config,
            )
        # Expose counts and provenance, but no logits, source path, or raw arrays.
        response = {
            # The database worker later replaces this temporary ID with its stable ID.
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
        # Validate types and required fields before the worker persists JSON.
        return AnalysisResponse.model_validate(response)
