from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.core.db.models import AnalysisStatus
from backend.services.analysis_service import recommendations_for


def analysis(*, result=None, quality=1.0, status=AnalysisStatus.completed, user_id=None):
    return SimpleNamespace(
        id=uuid4(), user_id=user_id or uuid4(), status=status,
        image_quality_score=quality, result=result,
    )


def safe_profile(**answers):
    return {
        "skin_sensitivity": "low",
        "known_product_allergy": "no",
        "severe_irritation": "no",
        **answers,
    }


def test_self_reported_fallback_is_available_when_wrinkle_gate_is_withheld():
    candidate = analysis(
        result={"recommendation_gate": {"eligible": False}, "experimental_score": {"regions": {"image_left_periocular": {"score": 99}}}},
    )

    result = recommendations_for(candidate, safe_profile(
        skin_type="dry", outdoor_minutes=90, sunscreen_frequency="sometimes",
    ))

    assert result["status"] == "ready"
    assert [item["category"] for item in result["recommendations"]] == [
        "fragrance-free moisturizer", "broad-spectrum sunscreen SPF 30+",
    ]
    assert all(item["signal_sources"] == ["self_reported"] for item in result["recommendations"])
    assert result["image_context"] == {
        "status": "withheld", "reason": "wrinkle_confidence_not_released",
    }


def test_only_calibrated_released_region_scores_can_be_combined_with_self_report():
    candidate = analysis(result={
        "recommendation_gate": {"eligible": True},
        "model_output": {
            "prediction_version": "prediction-v1",
            "confidence": {"calibration_status": "calibrated", "calibration_version": "calibration-v2"},
        },
        "derived_score": {
            "score_version": "area-v1", "roi_version": "roi-v1",
            "regions": {"image_left_periocular": {"score": 11.5}},
        },
        "experimental_score": {"regions": {"image_left_periocular": {"score": 99.0}}},
    })

    result = recommendations_for(candidate, safe_profile(skin_type="dry"))

    item = result["recommendations"][0]
    assert item["signal_sources"] == ["image", "self_reported"]
    assert item["wrinkle_regions"] == ["image_left_periocular"]
    assert item["wrinkle_region_scores"] == [{"region": "image_left_periocular", "score": 11.5}]
    assert result["image_context"]["score_version"] == "area-v1"
    assert result["image_context"]["regions"]["image_left_periocular"]["score"] == 11.5


def test_image_scores_with_missing_release_versions_are_withheld():
    candidate = analysis(result={
        "recommendation_gate": {"eligible": True},
        "model_output": {
            "prediction_version": "prediction-v1",
            "confidence": {"calibration_status": "calibrated", "calibration_version": None},
        },
        "derived_score": {
            "score_version": "area-v1", "roi_version": "roi-v1",
            "regions": {"image_left_periocular": {"score": 11.5}},
        },
    })

    result = recommendations_for(candidate, safe_profile(skin_type="dry"))

    assert result["image_context"] == {
        "status": "withheld", "reason": "wrinkle_provenance_incomplete",
    }
    assert result["recommendations"][0]["signal_sources"] == ["self_reported"]


@pytest.mark.parametrize("answers", [
    {"severe_irritation": True},
    {"known_product_allergy": True},
    {"skin_sensitivity": "high"},
])
def test_safety_exclusions_block_all_categories(answers):
    result = recommendations_for(analysis(), safe_profile(skin_type="dry", **answers))

    assert result["status"] == "safety_blocked"
    assert result["recommendations"] == []


def test_missing_safety_answers_block_recommendations():
    result = recommendations_for(analysis(), {"skin_type": "dry"})
    assert result["status"] == "safety_blocked"
    assert result["blocked_reason"] == "safety_screening_incomplete"


def test_recent_reported_daily_dryness_can_support_moisturizer_without_using_predictions():
    result = recommendations_for(
        analysis(),
        safe_profile(skin_type="normal"),
        {
            "status": "available",
            "reported_dryness_score_0_10": 7,
            "reported_dryness_date": "2026-09-28",
            # This synthetic prediction must have no effect on recommendation rules.
            "predicted_dryness_score_0_10": 10,
        },
    )

    assert result["recommendations"][0]["category"] == "fragrance-free moisturizer"
    assert result["recommendations"][0]["input_fields"] == ["reported_dryness_score_0_10"]
    assert result["recommendations"][0]["signal_sources"] == ["daily_health_reported"]
    assert result["recommendations"][0]["input_source"] == "daily_health_reported"


def test_image_plus_daily_dryness_preserves_the_actual_daily_trigger():
    candidate = analysis(result={
        "recommendation_gate": {"eligible": True},
        "model_output": {"prediction_version": "prediction-v1", "confidence": {"calibration_status": "calibrated", "calibration_version": "calibration-v2"}},
        "derived_score": {"score_version": "area-v1", "roi_version": "roi-v1", "regions": {"image_left_periocular": {"score": 11.5}}},
    })

    result = recommendations_for(
        candidate, safe_profile(skin_type="normal"),
        {"status": "available", "reported_dryness_score_0_10": 7, "reported_dryness_date": "2026-09-28"},
    )

    item = result["recommendations"][0]
    assert item["signal_sources"] == ["image", "daily_health_reported"]
    assert item["input_source"] == "image_and_daily_health_reported"
    assert "daily health tracker" in item["rationale"]
def test_recent_daily_outdoor_context_supports_sunscreen_without_claiming_sleep_or_water_effects():
    result = recommendations_for(
        analysis(), safe_profile(sunscreen_frequency="sometimes"),
        {
            "status": "no_recent_reported_dryness",
            "lifestyle": {
                "source_table": "daily_health_entries",
                "record_id": str(uuid4()),
                "observed_date": "2026-09-28",
                "outdoor_exposure_choice": 3,
                "sleep_duration_minutes": 300,
                "water_intake_ml": 500,
            },
        },
    )

    item = result["recommendations"][0]
    assert item["category"] == "broad-spectrum sunscreen SPF 30+"
    assert item["signal_sources"] == ["self_reported", "daily_health_reported"]
    assert item["input_source"] == "self_reported_and_daily_health_reported"
    assert item["input_fields"] == ["sunscreen_frequency", "daily_outdoor_exposure_choice"]
