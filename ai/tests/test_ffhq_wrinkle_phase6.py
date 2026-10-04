import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from ai.ffhq_wrinkle.confidence import (
    ConfidencePolicy,
    decision_margin_confidence,
    evaluate_confidence,
    load_confidence_policy,
)
from ai.ffhq_wrinkle.prediction import PredictionResult
from ai.ffhq_wrinkle.quality import QualityAssessment, QualityGateError
from ai.ffhq_wrinkle.scoring import (
    ROI_VERSION,
    SCORE_VERSION,
    build_regional_rois,
    derive_scores,
)
from backend.wrinkle.api import MAX_UPLOAD_BYTES, create_app
from backend.wrinkle.service import WrinkleAnalysisService


def calibrated_policy(threshold=0.5):
    return ConfidencePolicy(
        policy_version="test-policy-v1",
        method="mean-binary-decision-margin",
        status="calibrated",
        minimum_confidence=threshold,
        calibration_version="synthetic-test-only-v1",
        validation_dataset="synthetic-unit-test",
        sample_count=10,
        notes="Unit-test fixture, not production calibration.",
        model_architecture="UNet",
        checkpoint_sha256="a" * 64,
        prediction_version="prediction-v1",
        preprocessing_version="preprocess-v1",
        threshold_version="threshold-v1",
    )


def prediction(probability):
    probability = np.asarray(probability, dtype=np.float32)
    mask = probability >= 0.5
    metadata = {
        "prediction_version": "prediction-v1",
        "preprocessing_version": "preprocess-v1",
        "model": {
            "architecture": "UNet",
            "checkpoint_sha256": "a" * 64,
            "checkpoint": "must-not-leak.pth",
        },
        "threshold": {"version": "threshold-v1", "probability": 0.5},
        "wrinkle_pixels": int(mask.sum()),
        "face_pixels": int(mask.size),
        "artifacts": {"probability": "must-not-leak.png"},
    }
    return PredictionResult(
        logits=np.zeros((2, *probability.shape), dtype=np.float32),
        probability=probability,
        mask=mask,
        overlay=np.zeros((*probability.shape, 3), dtype=np.uint8),
        metadata=metadata,
    )


class ScoringTests(unittest.TestCase):
    def test_empty_policy_environment_uses_unreleased_default(self):
        with patch.dict("os.environ", {"APHRODIZE_WRINKLE_POLICY_BUNDLE": ""}):
            self.assertEqual(TestClient(create_app()).get("/health").status_code, 200)

    def test_all_scores_are_versioned_and_bounded(self):
        face = np.ones((100, 100), dtype=bool)
        wrinkle = np.zeros_like(face)
        wrinkle[20:25, 30:40] = True
        result = derive_scores(wrinkle, face, gate_passed=True)
        self.assertEqual(result["score_version"], SCORE_VERSION)
        self.assertEqual(result["roi_version"], ROI_VERSION)
        for score in [result["overall"], *result["regions"].values()]:
            self.assertEqual(score["score_version"], SCORE_VERSION)
            self.assertEqual(score["roi_version"], ROI_VERSION)
            self.assertGreaterEqual(score["score"], 0)
            self.assertLessEqual(score["score"], 100)

    def test_known_formula_and_gate(self):
        face = np.ones((10, 10), dtype=bool)
        wrinkle = np.zeros_like(face)
        wrinkle[0, 0] = True
        result = derive_scores(wrinkle, face, gate_passed=True)
        self.assertEqual(result["overall"]["score"], 20.0)
        with self.assertRaises(PermissionError):
            derive_scores(wrinkle, face, gate_passed=False)

    def test_rois_are_face_constrained(self):
        face = np.zeros((80, 120), dtype=bool)
        face[10:70, 20:100] = True
        rois = build_regional_rois(face)
        self.assertEqual(len(rois), 8)
        for roi in rois.values():
            self.assertEqual(roi.shape, face.shape)
            self.assertFalse(np.any(roi & ~face))


class ConfidenceTests(unittest.TestCase):
    def test_margin_and_low_confidence(self):
        face = np.ones((2, 2), dtype=bool)
        probability = np.array([[0.5, 0.5], [0.6, 0.4]], dtype=np.float32)
        self.assertAlmostEqual(decision_margin_confidence(probability, face), 0.1, places=6)
        result = evaluate_confidence(probability, face, calibrated_policy(0.2))
        self.assertFalse(result["passed"])
        self.assertEqual(result["reasons"], ["low_confidence"])

    def test_repository_policy_fails_closed(self):
        policy = load_confidence_policy()
        result = evaluate_confidence(np.ones((2, 2)), np.ones((2, 2)), policy)
        self.assertFalse(result["passed"])
        self.assertEqual(result["reasons"], ["confidence_not_calibrated"])


class ServiceTests(unittest.TestCase):
    def test_landmark_geometry_is_experimental_and_cannot_inherit_old_release(self):
        face = np.ones((8, 8), dtype=bool)
        roi = np.zeros_like(face)
        roi[2:4, 2:4] = True
        service = WrinkleAnalysisService(confidence_policy=calibrated_policy())
        response = service.build_response(prediction(np.full((8, 8), .95)), face,
                                          regional_rois={"forehead": roi})
        self.assertIsNone(response.derived_score)
        self.assertFalse(response.recommendation_gate.eligible)
        self.assertIn("landmark_roi_not_calibrated", response.recommendation_gate.reasons)
        self.assertEqual(response.experimental_score.roi_version, "mediapipe-landmark-skin-roi-v1")
        self.assertEqual(response.experimental_score.regions["forehead"].evaluated_pixels, 4)
        self.assertEqual(response.model_output.regional_geometry_status, "available")

    def test_missing_landmarks_keeps_overall_but_withholds_regions(self):
        response = WrinkleAnalysisService().build_response(
            prediction(np.full((8, 8), .95)), np.ones((8, 8), dtype=bool), regional_rois={}
        )
        self.assertEqual(response.experimental_score.regions, {})
        self.assertEqual(response.model_output.regional_geometry_status, "unavailable")

    def test_owner_review_releases_only_the_approved_model_without_calibration_claims(self):
        policy = load_confidence_policy(
            Path(__file__).resolve().parents[1] / "ffhq_wrinkle" / "reviewed_policy.json"
        )
        result = prediction(np.full((4, 4), 0.95))
        result.metadata.update({
            "prediction_version": policy.prediction_version,
            "preprocessing_version": policy.preprocessing_version,
            "model": {"architecture": policy.model_architecture,
                      "checkpoint_sha256": policy.checkpoint_sha256},
            "threshold": {"version": policy.threshold_version, "probability": 0.5},
        })
        service = WrinkleAnalysisService(confidence_policy=policy)
        payload = service.build_response(result, np.ones((4, 4))).model_dump()
        self.assertTrue(payload["recommendation_gate"]["eligible"])
        self.assertIsNotNone(payload["derived_score"])
        confidence = payload["model_output"]["confidence"]
        self.assertEqual(confidence["release_basis"], "manual_review")
        self.assertEqual(confidence["calibration_status"], "not_calibrated")
        self.assertIsNone(confidence["calibration_version"])
        self.assertIsNone(confidence["minimum_confidence"])
        self.assertEqual(confidence["validation_sample_count"], 0)
        with self.assertRaises(ValueError):
            replace(policy, approval_reference=None).validate()
        with self.assertRaises(ValueError):
            replace(policy, sample_count=10).validate()
        empty_face = service.build_response(result, np.zeros((4, 4))).model_dump()
        self.assertFalse(empty_face["recommendation_gate"]["eligible"])
        result.metadata["model"]["checkpoint_sha256"] = "b" * 64
        mismatched = service.build_response(result, np.ones((4, 4))).model_dump()
        self.assertFalse(mismatched["recommendation_gate"]["eligible"])
        self.assertIn(
            "policy_checkpoint_sha256_mismatch", mismatched["recommendation_gate"]["reasons"]
        )

    def test_uncalibrated_response_abstains_before_recommendation(self):
        calls = []
        service = WrinkleAnalysisService(recommendation_provider=lambda score: calls.append(score))
        response = service.build_response(prediction(np.full((4, 4), 0.95)), np.ones((4, 4)))
        payload = response.model_dump()
        self.assertEqual(payload["status"], "abstained")
        self.assertIsNone(payload["derived_score"])
        self.assertGreaterEqual(payload["experimental_score"]["overall"]["score"], 0)
        self.assertEqual(payload["recommendations"], [])
        self.assertEqual(calls, [])
        encoded = json.dumps(payload)
        self.assertNotIn("must-not-leak", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_calibrated_response_separates_model_and_derived_output(self):
        service = WrinkleAnalysisService(confidence_policy=calibrated_policy(0.5))
        response = service.build_response(prediction(np.full((4, 4), 0.95)), np.ones((4, 4)))
        payload = response.model_dump()
        self.assertEqual(payload["status"], "completed")
        self.assertIn("output_types", payload["model_output"])
        self.assertEqual(payload["derived_score"]["score_version"], SCORE_VERSION)
        self.assertFalse(payload["model_output"]["artifacts_publicly_available"])

    def test_policy_for_different_model_lineage_abstains(self):
        policy = replace(calibrated_policy(0.5), checkpoint_sha256="b" * 64)
        service = WrinkleAnalysisService(confidence_policy=policy)
        payload = service.build_response(
            prediction(np.full((4, 4), 0.95)), np.ones((4, 4))
        ).model_dump()
        self.assertEqual(payload["status"], "abstained")
        self.assertIn(
            "policy_checkpoint_sha256_mismatch",
            payload["model_output"]["confidence"]["reasons"],
        )

    def test_temporary_artifacts_are_removed(self):
        observed = {}

        def fake_predictor(source, output, **_kwargs):
            observed["source"] = Path(source)
            observed["output"] = Path(output)
            Path(output).mkdir()
            Image.fromarray(np.ones((4, 4), dtype=np.uint8) * 255).save(
                Path(output) / "face_mask.png"
            )
            Image.new("RGB", (4, 4), "gray").save(Path(output) / "aligned_face.png")
            return prediction(np.full((4, 4), 0.95))

        service = WrinkleAnalysisService(
            predictor=fake_predictor,
            model_loader=lambda *_args, **_kwargs: object(),
        )
        response = service.analyze_bytes(b"fake", ".jpg")
        self.assertEqual(response.status, "abstained")
        self.assertFalse(observed["source"].exists())
        self.assertFalse(observed["output"].exists())


class FakeService:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = 0

    def analyze_bytes(self, _data, _suffix):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


class ApiTests(unittest.TestCase):
    def response(self):
        return WrinkleAnalysisService().build_response(
            prediction(np.full((4, 4), 0.95)), np.ones((4, 4))
        )

    def test_consent_is_checked_before_service(self):
        fake = FakeService(self.response())
        client = TestClient(create_app(fake))
        result = client.post(
            "/v1/wrinkle/analyze",
            files={"image": ("face.jpg", b"image", "image/jpeg")},
            data={"consent_accepted": "false"},
        )
        self.assertEqual(result.status_code, 403)
        self.assertEqual(fake.calls, 0)

    def test_quality_rejection_is_sanitized(self):
        assessment = QualityAssessment(False, ("image_too_blurry",), {"secret": 1})
        fake = FakeService(error=QualityGateError(assessment))
        client = TestClient(create_app(fake))
        result = client.post(
            "/v1/wrinkle/analyze",
            files={"image": ("face.png", b"image", "image/png")},
            data={"consent_accepted": "true"},
        )
        self.assertEqual(result.status_code, 422)
        self.assertEqual(result.json()["quality_flags"], ["image_too_blurry"])
        self.assertNotIn("secret", result.text)

    def test_media_type_and_size_are_rejected_before_service(self):
        fake = FakeService(self.response())
        client = TestClient(create_app(fake))
        wrong = client.post(
            "/v1/wrinkle/analyze",
            files={"image": ("face.gif", b"gif", "image/gif")},
            data={"consent_accepted": "true"},
        )
        large = client.post(
            "/v1/wrinkle/analyze",
            files={"image": ("face.jpg", b"x" * (MAX_UPLOAD_BYTES + 1), "image/jpeg")},
            data={"consent_accepted": "true"},
        )
        self.assertEqual(wrong.status_code, 415)
        self.assertEqual(large.status_code, 413)
        self.assertEqual(fake.calls, 0)

    def test_success_contract_and_health(self):
        fake = FakeService(self.response())
        client = TestClient(create_app(fake))
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        result = client.post(
            "/v1/wrinkle/analyze",
            files={"image": ("face.webp", b"image", "image/webp")},
            data={"consent_accepted": "true"},
        )
        self.assertEqual(result.status_code, 200)
        self.assertIn("model_output", result.json())
        self.assertIn("derived_score", result.json())


if __name__ == "__main__":
    unittest.main()
