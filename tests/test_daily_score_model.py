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
