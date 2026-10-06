import json
from datetime import date, timedelta
from uuid import uuid4

import joblib
import pytest

from backend.core.db.models import DailyHealthOutcome
from backend.libs.model_loader import get_daily_score_model
from backend.services import daily_health_training as training
from backend.services.daily_health_forecast_receipt import (
    issue_forecast_receipt,
    verify_forecast_receipt,
)
from backend.services.daily_health_training import (
    ENERGY_TARGET_NAMES,
    build_next_day_training_examples,
)
from tests.test_daily_health_training import _entry


class FixedModel:
    def __init__(self, values):
        self.values = values

    def predict(self, _inputs):
        return [self.values]


def prediction(*, energy=True, synthetic=False, sleep_hours=7):
    values = [6.0, 5.0, 8.0] if energy else [6.0, 5.0]
    metadata = {
        "model_id": "daily-health-next-day-0123456789abcdef", "model_family": "test",
        "prediction_horizon_days": 0 if synthetic else 1,
        "targets": ENERGY_TARGET_NAMES if energy else ENERGY_TARGET_NAMES[:2],
        "data_policy": "synthetic" if synthetic else
            "active_opt_in_and_user_reported_numeric_outcomes_only",
    }
    if synthetic:
        values = values[:2]
    return get_daily_score_model().predict_daily_health(
        local_date=date(2026, 10, 5), sleep_hours=sleep_hours, sleep_minutes=0,
        water_intake_ml=1400, outdoor_exposure_choice=1, weight_kg=60, age_band="18_60",
        model_bundle={"metadata": metadata, "model": FixedModel(values)},
    )


def test_real_model_exposes_numeric_next_day_energy_and_thirst_not_hydration_formula():
    result = prediction()
    signals = result["interpretation"]["next_day_predictions"]
    assert signals["thirst_attention"]["value_0_10"] == 6.0
    assert signals["low_energy_signal"]["value_0_10"] == 8.0
    assert signals["thirst_attention"]["target_date"] == "2026-10-06"
    assert signals["thirst_attention"]["level"] is None
    assert result["predictions"]["thirst_score_0_10"]["status"] == "calculated"
    assert "acne_flare_signal" not in result["interpretation"]


def test_old_two_target_candidate_does_not_invent_energy():
    signals = prediction(energy=False)["interpretation"]["next_day_predictions"]
    assert signals["thirst_attention"]["status"] == "predicted"
    assert signals["low_energy_signal"]["status"] == "model_not_ready"
    assert "value_0_10" not in signals["low_energy_signal"]


def test_synthetic_and_out_of_domain_results_do_not_enable_observed_forecasts():
    for result in [prediction(synthetic=True), prediction(sleep_hours=1)]:
        assert issue_forecast_receipt(result) is None
        assert all(signal["status"] != "predicted"
                   for signal in result["interpretation"]["next_day_predictions"].values())


def test_receipt_binds_saved_outputs_to_server_input_and_rejects_tampering():
    result = prediction()
    token = issue_forecast_receipt(result)
    inputs = dict(local_date=date(2026, 10, 5), sleep_minutes=420, water_ml=1400, outdoors=1)
    signals = verify_forecast_receipt(token, **inputs)
    assert signals["low_energy_signal"]["value_0_10"] == 8
    with pytest.raises(ValueError):
        verify_forecast_receipt(token, **{**inputs, "water_ml": 1500})
    with pytest.raises(ValueError):
        verify_forecast_receipt("invalid-token", **inputs)


def test_energy_examples_require_actual_report_and_same_account_previous_day():
    owner, other = uuid4(), uuid4()
    day = date(2026, 10, 5)
    outcome = DailyHealthOutcome(user_id=owner, target_date=day + timedelta(days=1),
                                reported_thirst_level_0_10=6, reported_dryness_level_0_10=5,
                                reported_energy_level_0_10=0)
    entries = [_entry(owner, day), _entry(other, day)]
    examples = build_next_day_training_examples(entries, [outcome],
                                                consented_user_ids={owner}, include_energy=True)
    assert examples[0].target_values == (6, 5, 0)
    outcome.reported_energy_level_0_10 = None
    assert build_next_day_training_examples(entries, [outcome],
                                           consented_user_ids={owner}, include_energy=True) == []


@pytest.mark.asyncio
async def test_energy_pipeline_writes_three_targets_and_two_baselines(tmp_path, monkeypatch):
    rows = [training.TrainingExample(
        participant_id=f"test-{user}", target_date=date(2026, 1, 1) + timedelta(days=day),
        feature_values=(float(360 + day * 3), float(1000 + day * 20), 1.0),
        target_values=(float(day % 8), float(day % 6), float(day % 10)),
    ) for user in range(5) for day in range(25)]

    async def preferred(_session):
        return rows, ENERGY_TARGET_NAMES

    async def current(_session, *, include_energy):
        assert include_energy
        return rows

    class Session:
        async def scalar(self, _statement):
            return None

        async def commit(self):
            pass

        def add(self, _version):
            pass

    monkeypatch.setattr(training, "load_preferred_training_examples", preferred)
    monkeypatch.setattr(training, "load_consent_filtered_training_examples", current)
    monkeypatch.setattr(training, "ARTIFACT_ROOT", tmp_path / "candidates")
    monkeypatch.setattr(training, "REPOSITORY_ROOT", tmp_path)
    version = await training.train_daily_health_candidate(Session())
    assert version.status == "candidate"
    artifact = tmp_path / version.artifact_uri
    assert joblib.load(artifact).n_outputs_ == 3
    manifest = json.loads((artifact.parent / "manifest.json").read_text())
    assert manifest["targets"] == ENERGY_TARGET_NAMES
    for split in ("test", "test_mean_baseline", "temporal_test", "temporal_mean_baseline"):
        assert "reported_energy_level_0_10" in manifest["metrics"][split]
