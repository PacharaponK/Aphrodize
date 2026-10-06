from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.v1.router import api_router
from backend.api.v1.routes.daily_health import router
from backend.core.config import settings
from backend.core.db.session import get_session
from backend.libs.model_loader import get_daily_score_model


def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    async def empty_session():
        yield EmptySession()

    app.dependency_overrides[get_session] = empty_session
    return TestClient(app)


class EmptySession:
    async def get(self, *_args):
        return None


def test_guidance_includes_only_relevant_actionable_items() -> None:
    model = get_daily_score_model()

    assert model.make_guidance(480, 2.0, 2.0, 1) == []

    guidance = model.make_guidance(360, 8.0, 8.0, 3)
    assert len(guidance) == 4
    assert any("เวลานอน 6 ชั่วโมง 0 นาที" in item for item in guidance)
    assert any("ความกระหาย" in item for item in guidance)
    assert any("รู้สึกแห้ง" in item for item in guidance)
    assert any("ครีมกันแดด" in item for item in guidance)
    assert all("คุณภาพ" not in item and "ไม่ได้ยืนยัน" not in item for item in guidance)


def test_sleep_guidance_uses_optional_age_band_or_age_neutral_wording() -> None:
    model = get_daily_score_model()

    teen_guidance = model.make_guidance(450, None, None, 1, age_band="13_17")
    adult_guidance = model.make_guidance(390, None, None, 1, age_band="18_60")
    unspecified_guidance = model.make_guidance(390, None, None, 1)

    assert any("13–17 ปี" in item and "8–10 ชั่วโมง" in item for item in teen_guidance)
    assert any("18–60 ปี" in item and "7 ชั่วโมง" in item for item in adult_guidance)
    assert all("18–60 ปี" not in item for item in unspecified_guidance)
    assert any("ต่างกันตามวัย" in item for item in unspecified_guidance)


def test_promoted_daily_score_model_loads_and_returns_expected_contract() -> None:
    model = get_daily_score_model()
    result = model.predict_daily_health(
        local_date=date(2026, 9, 26),
        sleep_hours=6,
        sleep_minutes=2,
        water_intake_ml=1400,
        weight_kg=60,
        outdoor_exposure_choice=2,
    )

    assert result["model"]["model_id"] == "daily-score-random-forest-synthetic-v1"
    assert result["calculated"]["sleep_score_0_100"] == 67.0
    assert 0 <= result["predictions"]["thirst_score_0_10"]["value"] <= 10
    assert result["predictions"]["thirst_score_0_10"]["value"] == 2.2
    assert result["predictions"]["thirst_score_0_10"]["status"] == "calculated"
    assert 0 <= result["predictions"]["skin_dryness_score_0_10"]["value"] <= 10
    assert result["guidance"]
    assert result["warnings"]
    assert result["prediction_target_date"] == "2026-09-26"


def test_user_candidate_bundle_forecasts_the_next_day_and_is_identified_as_experimental() -> None:
    model = get_daily_score_model()

    result = model.predict_daily_health(
        local_date=date(2026, 9, 26),
        sleep_hours=7,
        sleep_minutes=20,
        water_intake_ml=1400,
        weight_kg=60,
        outdoor_exposure_choice=2,
        model_bundle={
            "model": get_daily_score_model().load_model_bundle()["model"],
            "metadata": {
                "model_id": "daily-health-next-day-0123456789abcdef",
                "model_family": "daily_health_next_day_random_forest",
                "data_policy": "active_opt_in_and_user_reported_numeric_outcomes_only",
                "prediction_horizon_days": 1,
                "holdout": {"metrics": {"reported_thirst_level_0_10": {"mae": 1.0}}},
            },
        },
    )

    assert result["prediction_target_date"] == "2026-09-27"
    assert result["predictions"]["thirst_score_0_10"]["target_date"] == "2026-09-26"
    assert result["predictions"]["thirst_score_0_10"]["value"] == 2.2
    assert result["model"]["model_id"] == "daily-health-next-day-0123456789abcdef"
    assert result["model_status"] == "experimental_user_reported_candidate"
    assert any("ผลที่ผู้ใช้รายงานเอง" in warning for warning in result["warnings"])
    assert all("ข้อมูลสังเคราะห์" not in warning for warning in result["warnings"])


def test_prediction_api_abstains_outside_model_training_domain() -> None:
    response = client().post(
        "/predict",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 6,
            "sleep_minutes": 2,
            "water_intake_ml": 400,
            "outdoor_exposure_choice": 1,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["predictions"]["thirst_score_0_10"]["value"] is None
    assert result["predictions"]["thirst_score_0_10"]["status"] == "not_available"
    assert result["predictions"]["skin_dryness_score_0_10"]["value"] is None
    assert result["calculated"]["sleep_score_0_100"] == 67.0
    assert result["input_domain_status"] == "out_of_training_domain"
    assert result["input_domain_reasons"] == ["water_intake_outside_training_range"]
    assert result["prediction_status"] == "abstained"
    assert result["prediction_mode"] == "standard"
    assert result["interpretation"]["daily_health_summary"]["level"] is None


def test_test_prediction_api_returns_flagged_scores_outside_training_domain() -> None:
    response = client().post(
        "/predict/test",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 6,
            "sleep_minutes": 2,
            "water_intake_ml": 400,
            "weight_kg": 60,
            "outdoor_exposure_choice": 1,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["input_domain_status"] == "out_of_training_domain"
    assert result["prediction_mode"] == "test_only"
    assert result["prediction_status"] == "experimental_out_of_domain"
    assert result["predictions"]["thirst_score_0_10"]["status"] == "calculated"
    assert result["predictions"]["thirst_score_0_10"]["value"] == 7.8
    assert result["predictions"]["thirst_score_0_10"]["value"] is not None
    assert result["predictions"]["skin_dryness_score_0_10"]["value"] is not None
    assert result["interpretation"]["daily_health_summary"]["status"] == "out_of_training_domain"
    assert any("เวลานอน" in item for item in result["guidance"])
    assert all("กระหาย" not in item and "ผิวรู้สึกแห้ง" not in item for item in result["guidance"])
    assert any("นอกช่วงฝึก" in warning for warning in result["warnings"])


def test_prediction_api_returns_two_scores_for_in_domain_input() -> None:
    response = client().post(
        "/predict",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 7,
            "sleep_minutes": 20,
            "water_intake_ml": 1400,
            "weight_kg": 60,
            "outdoor_exposure_choice": 2,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["predictions"]["thirst_score_0_10"]["status"] == "calculated"
    assert result["predictions"]["skin_dryness_score_0_10"]["status"] == "predicted"
    assert result["input_domain_status"] == "in_domain"
    assert result["prediction_status"] == "predicted"
    assert result["interpretation"]["daily_health_summary"]["level"] in {
        "low",
        "moderate",
        "high",
    }
    assert result["interpretation"]["next_day_predictions"]["low_energy_signal"]["status"] == (
        "model_not_ready"
    )
    assert "acne_flare_signal" not in result["interpretation"]


def test_sleep_attention_uses_consented_age_band_without_inventing_a_clinical_risk() -> None:
    model = get_daily_score_model()
    age_specific = model.build_health_interpretation(
        sleep_minutes=450,
        thirst_score=2.0,
        dryness_score=2.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
        age_band="13_17",
    )
    age_unspecified = model.build_health_interpretation(
        sleep_minutes=450,
        thirst_score=2.0,
        dryness_score=2.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
    )

    assert age_specific["daily_health_summary"]["level"] == "moderate"
    assert any(
        "13–17 ปี" in item for item in age_specific["daily_health_summary"]["recommendations"]
    )
    assert age_unspecified["daily_health_summary"]["level"] == "low"


def test_prediction_api_personal_guidance_requires_and_uses_explicit_consent() -> None:
    payload = {
        "local_date": "2026-09-26",
        "sleep_hours": 7,
        "sleep_minutes": 20,
        "water_intake_ml": 1400,
        "outdoor_exposure_choice": 2,
        "personal_context": {
            "consent_given": True,
            "age_guidance_consent_given": True,
            "age_band": "18_60",
            "smoking_status": "current",
            "currently_menstruating": True,
        },
    }
    response = client().post("/predict", json=payload)

    assert response.status_code == 200
    result = response.json()
    guidance = result["interpretation"]["profile_guidance"]
    assert {item["topic"] for item in guidance} == {"smoking", "menstrual_wellbeing"}
    assert all(item["message"] in result["guidance"] for item in guidance)

    payload["personal_context"]["consent_given"] = False
    rejected = client().post("/predict", json=payload)
    assert rejected.status_code == 422


def test_daily_attention_uses_only_three_levels_and_short_related_guidance() -> None:
    model = get_daily_score_model()

    low = model.build_health_interpretation(
        sleep_minutes=480,
        thirst_score=2.0,
        dryness_score=2.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
    )
    moderate = model.build_health_interpretation(
        sleep_minutes=390,
        thirst_score=4.5,
        dryness_score=5.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
    )
    high = model.build_health_interpretation(
        sleep_minutes=330,
        thirst_score=8.0,
        dryness_score=8.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
    )

    assert low["daily_health_summary"]["level"] == "low"
    assert moderate["daily_health_summary"]["level"] == "moderate"
    assert high["daily_health_summary"]["level"] == "high"
    assert "ผิวอาจรู้สึกแห้งหรือตึง" in moderate["daily_health_summary"]["possible_signals"]
    assert "สิว" not in " ".join(moderate["daily_health_summary"]["possible_signals"])


def test_personal_profile_guidance_requires_context_and_does_not_change_risk_level() -> None:
    model = get_daily_score_model()
    base = model.build_health_interpretation(
        sleep_minutes=480,
        thirst_score=2.0,
        dryness_score=2.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
    )
    personalized = model.build_health_interpretation(
        sleep_minutes=480,
        thirst_score=2.0,
        dryness_score=2.0,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
        smoking_status="current",
        currently_menstruating=True,
    )

    assert personalized["daily_health_summary"]["level"] == base["daily_health_summary"]["level"]
    assert {item["topic"] for item in personalized["profile_guidance"]} == {
        "smoking",
        "menstrual_wellbeing",
    }


def test_prediction_api_accepts_10_hours_and_caps_sleep_score_at_9_hours() -> None:
    test_client = client()
    response = test_client.post(
        "/predict",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 10,
            "sleep_minutes": 0,
            "water_intake_ml": 1400,
            "outdoor_exposure_choice": 2,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["calculated"]["sleep_score_0_100"] == 100.0
    assert result["input_domain_status"] == "out_of_training_domain"
    assert result["predictions"]["thirst_score_0_10"]["value"] is None

    too_long = test_client.post(
        "/predict",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 10,
            "sleep_minutes": 1,
            "water_intake_ml": 1400,
            "outdoor_exposure_choice": 2,
        },
    )
    assert too_long.status_code == 422


def test_versioned_backend_prediction_route_requires_and_accepts_api_credentials(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "api_username", "test-user")
    monkeypatch.setattr(settings, "api_password", "test-password")
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    async def empty_session():
        yield EmptySession()

    app.dependency_overrides[get_session] = empty_session
    test_client = TestClient(app)
    payload = {
        "local_date": "2026-09-26",
        "sleep_hours": 7,
        "sleep_minutes": 20,
        "water_intake_ml": 1400,
        "outdoor_exposure_choice": 2,
    }

    unauthorized = test_client.post("/api/v1/daily-health/predict", json=payload)
    authorized = test_client.post(
        "/api/v1/daily-health/predict", json=payload, auth=("test-user", "test-password")
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


@pytest.mark.parametrize(
    ("water", "score", "range_status"),
    [
        (0, 10.0, "below_reference"),
        (900, 5.0, "below_reference"),
        (1800, 0.0, "within_reference"),
        (2100, 0.0, "within_reference"),
        (2500, 0.0, "above_reference"),
    ],
)
def test_weight_based_thirst_formula_boundaries(water, score, range_status) -> None:
    hydration = get_daily_score_model().calculate_hydration(water, 60)
    assert hydration["score_0_10"] == score
    assert hydration["reference_lower_ml"] == 1800
    assert hydration["reference_upper_ml"] == 2100
    assert hydration["range_status"] == range_status
    assert hydration["recorded_shortfall_ml"] == max(0, 1800 - water)


def test_thirst_uses_fractional_weight_and_does_not_invent_missing_weight() -> None:
    model = get_daily_score_model()
    assert model.calculate_hydration(900, 60.5)["reference_lower_ml"] == 1815
    missing = model.calculate_hydration(900, None)
    assert missing["score_0_10"] is None
    assert missing["range_status"] == "missing_weight"
    teen = model.calculate_hydration(900, 60, "13_17")
    assert teen["score_0_10"] is None
    assert teen["range_status"] == "unsupported_age"


@pytest.mark.parametrize("weight", [0, -60, 501, float("nan"), float("inf")])
def test_api_rejects_invalid_weight(weight) -> None:
    from pydantic import ValidationError

    from backend.api.schemas.daily_health import DailyHealthPredictionRequest

    with pytest.raises(ValidationError):
        DailyHealthPredictionRequest(
            local_date=date(2026, 9, 26),
            sleep_hours=7,
            sleep_minutes=0,
            water_intake_ml=1400,
            outdoor_exposure_choice=1,
            weight_kg=weight,
        )


def test_formula_thirst_remains_available_outside_dryness_training_domain() -> None:
    result = (
        client()
        .post(
            "/predict",
            json={
                "local_date": "2026-09-26",
                "sleep_hours": 10,
                "sleep_minutes": 0,
                "water_intake_ml": 2500,
                "outdoor_exposure_choice": 4,
                "weight_kg": 70,
            },
        )
        .json()
    )
    assert result["predictions"]["thirst_score_0_10"]["status"] == "calculated"
    assert result["predictions"]["thirst_score_0_10"]["value"] == 0
    assert result["predictions"]["skin_dryness_score_0_10"]["value"] is None
    assert result["calculated"]["hydration"]["reference_lower_ml"] == 2100
    assert result["calculated"]["hydration"]["reference_upper_ml"] == 2450


def test_intake_gap_does_not_infer_skin_dryness_or_subjective_thirst() -> None:
    result = get_daily_score_model().build_health_interpretation(
        sleep_minutes=480,
        thirst_score=8,
        dryness_score=2,
        outdoor_exposure_choice=1,
        input_domain_status="in_domain",
        thirst_is_calculated=True,
    )
    assert result["skin_care_attention_level"]["level"] == "low"
    assert result["daily_health_summary"]["level"] == "high"
    assert result["daily_health_summary"]["possible_signals"] == ["น้ำที่บันทึกยังต่ำกว่าช่วงอ้างอิงตามน้ำหนัก"]
