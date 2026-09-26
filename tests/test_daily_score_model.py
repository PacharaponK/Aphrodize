from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.v1.router import api_router
from backend.api.v1.routes.daily_health import router
from backend.core.config import settings
from backend.libs.model_loader import get_daily_score_model


def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_guidance_includes_only_relevant_actionable_items() -> None:
    model = get_daily_score_model()

    assert model.make_guidance(480, 2.0, 2.0, 1) == []

    guidance = model.make_guidance(360, 8.0, 8.0, 3)
    assert len(guidance) == 4
    assert any("เวลานอน 6 ชั่วโมง 0 นาที" in item for item in guidance)
    assert any("thirst" in item for item in guidance)
    assert any("ผิวแห้ง" in item for item in guidance)
    assert any("ป้องกันแดด" in item for item in guidance)
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
        outdoor_exposure_choice=2,
    )

    assert result["model"]["model_id"] == "daily-score-random-forest-synthetic-v1"
    assert result["calculated"]["sleep_score_0_100"] == 86.2
    assert 0 <= result["predictions"]["thirst_score_0_10"]["value"] <= 10
    assert 0 <= result["predictions"]["skin_dryness_score_0_10"]["value"] <= 10
    assert result["guidance"]
    assert result["warnings"]


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
    assert result["predictions"]["thirst_score_0_10"] == {
        "value": None,
        "status": "not_available",
    }
    assert result["predictions"]["skin_dryness_score_0_10"]["value"] is None
    assert result["calculated"]["sleep_score_0_100"] == 86.2
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
            "outdoor_exposure_choice": 1,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["input_domain_status"] == "out_of_training_domain"
    assert result["prediction_mode"] == "test_only"
    assert result["prediction_status"] == "experimental_out_of_domain"
    assert result["predictions"]["thirst_score_0_10"]["status"] == "experimental_out_of_domain"
    assert result["predictions"]["thirst_score_0_10"]["value"] is not None
    assert result["predictions"]["skin_dryness_score_0_10"]["value"] is not None
    assert result["interpretation"]["daily_health_summary"]["status"] == "out_of_training_domain"
    assert result["guidance"] == []
    assert any("นอกช่วงฝึก" in warning for warning in result["warnings"])


def test_prediction_api_returns_two_scores_for_in_domain_input() -> None:
    response = client().post(
        "/predict",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 7,
            "sleep_minutes": 20,
            "water_intake_ml": 1400,
            "outdoor_exposure_choice": 2,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["predictions"]["thirst_score_0_10"]["status"] == "predicted"
    assert result["predictions"]["skin_dryness_score_0_10"]["status"] == "predicted"
    assert result["input_domain_status"] == "in_domain"
    assert result["prediction_status"] == "predicted"
    assert result["interpretation"]["daily_health_summary"]["level"] in {
        "low",
        "moderate",
        "high",
    }
    assert result["interpretation"]["next_day_predictions"]["low_energy_signal"]["status"] == (
        "insufficient_history"
    )
    assert result["interpretation"]["acne_flare_signal"]["status"] == "insufficient_data"


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
        "13–17 ปี" in item
        for item in age_specific["daily_health_summary"]["recommendations"]
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
    guidance = response.json()["interpretation"]["profile_guidance"]
    assert {item["topic"] for item in guidance} == {"smoking", "menstrual_wellbeing"}

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


def test_prediction_api_rejects_sleep_above_supported_input_limit() -> None:
    response = client().post(
        "/predict",
        json={
            "local_date": "2026-09-26",
            "sleep_hours": 9,
            "sleep_minutes": 1,
            "water_intake_ml": 1400,
            "outdoor_exposure_choice": 2,
        },
    )

    assert response.status_code == 422


def test_versioned_backend_prediction_route_requires_and_accepts_api_credentials(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "api_username", "test-user")
    monkeypatch.setattr(settings, "api_password", "test-password")
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
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
