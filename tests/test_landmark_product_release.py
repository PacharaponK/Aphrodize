from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai.ffhq_wrinkle.confidence import load_confidence_policy
from backend.core.db.models import AnalysisStatus
from backend.services.analysis_service import attach_catalog_products, recommendations_for
from backend.services.fixture_service import products_from_fixture

ROOT = Path(__file__).resolve().parents[1]
PROFILE = {
    "skin_type": "dry", "age_group": "25_34", "skin_sensitivity": "low",
    "known_product_allergy": "no", "severe_irritation": "no",
    "sunscreen_frequency": "every_day",
}


def saved_landmark_result(region="image_right_periocular"):
    policy = load_confidence_policy(ROOT / "ai/ffhq_wrinkle/reviewed_policy.json")
    return SimpleNamespace(status=AnalysisStatus.completed, image_quality_score=1, result={
        "recommendation_gate": {"eligible": False, "reasons": ["landmark_roi_not_calibrated"]},
        "derived_score": None,
        "experimental_score": {
            "score_version": "aphrodize-wrinkle-area-v1", "roi_version": policy.roi_version,
            "regions": {region: {
                "score": 100, "wrinkle_pixels": 500, "evaluated_pixels": 10000,
            }},
        },
        "model_output": {
            "architecture": policy.model_architecture,
            "checkpoint_sha256": policy.checkpoint_sha256,
            "prediction_version": policy.prediction_version,
            "preprocessing_version": policy.preprocessing_version,
            "threshold_version": policy.threshold_version,
            "regional_geometry_status": "available",
            "confidence": {
                "passed": True, "release_basis": "manual_review",
                "approval_reference": "previous-owner-release", "policy_version": "old-policy",
                "calibration_status": "not_calibrated",
            },
        },
    })


@pytest.mark.parametrize("region,rule,area", [
    ("image_right_periocular", "R-WRINKLE-EYE-001", "eye_contour"),
    ("forehead", "R-WRINKLE-FACE-001", "face"),
])
def test_saved_landmark_results_match_actual_catalog_without_rewriting_results(region, rule, area):
    analysis = saved_landmark_result(region)
    before = deepcopy(analysis.result)
    response = recommendations_for(analysis, PROFILE)
    products = products_from_fixture(ROOT / "backend/fixtures/products.yaml")
    attach_catalog_products(response, products)
    targeted = next(item for item in response["recommendations"] if item["rule_id"] == rule)
    assert targeted["products"]
    assert all(area in product["application_regions"] for product in targeted["products"])
    assert response["image_context"]["status"] == "eligible"
    assert response["image_context"]["release_basis"] == "manual_review"
    assert response["image_context"]["calibration_version"] is None
    assert analysis.result == before


@pytest.mark.parametrize("section,field,value", [
    ("model_output", "checkpoint_sha256", "wrong-model"),
    ("model_output", "preprocessing_version", "wrong-pipeline"),
    ("model_output", "regional_geometry_status", "unavailable"),
    ("experimental_score", "roi_version", "unapproved-roi"),
    ("experimental_score", "score_version", "unapproved-score"),
    ("recommendation_gate", "reasons", ["landmark_roi_not_calibrated", "low_confidence"]),
])
def test_saved_landmark_release_rejects_other_models_geometry_and_failures(section, field, value):
    analysis = saved_landmark_result()
    analysis.result[section][field] = value
    response = recommendations_for(analysis, PROFILE)
    assert response["image_context"]["status"] == "withheld"
    assert all(not item["rule_id"].startswith("R-WRINKLE") for item in response["recommendations"])


def test_saved_landmark_release_preserves_quality_and_profile_screening():
    analysis = saved_landmark_result()
    analysis.image_quality_score = .79
    assert recommendations_for(analysis, PROFILE)["image_context"]["status"] == "withheld"
    analysis.image_quality_score = 1
    for overrides in [{"skin_sensitivity": "high"}, {"known_product_allergy": "yes"}]:
        assert recommendations_for(analysis, {**PROFILE, **overrides})["status"] == "safety_blocked"
    response = recommendations_for(analysis, {**PROFILE, "age_group": "13_17"})
    assert all(not item["rule_id"].startswith("R-WRINKLE") for item in response["recommendations"])
