"""Exercise UV safety gates, delayed labels and reversible deployment offline."""

import csv
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from backend.services import uv_lifecycle as lifecycle
from scripts import train_uv_model, uv_mlops


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle, "MODELS", tmp_path / "models")
    monkeypatch.setattr(lifecycle, "ARTIFACTS", tmp_path / "artifacts")
    monkeypatch.setattr(train_uv_model, "DATA", tmp_path / "data.csv")
    return tmp_path


def make_bundle(version="uv-test", cutoff="2026-01-01"):
    bundle = lifecycle.bundle_path(version)
    (bundle / "models").mkdir(parents=True)
    (bundle / "artifacts").mkdir()
    for city in lifecycle.CITIES:
        (bundle / "models" / f"{city}.pkl").write_bytes(b"trusted test placeholder")
    (bundle / "dataset.csv").write_text("test", encoding="utf-8")
    lifecycle.atomic_json(bundle / "artifacts/metrics.json", {})
    lifecycle.seal_bundle(
        bundle,
        {
            "source_sha256": lifecycle.digest(bundle / "dataset.csv"),
            "trained_through": dict.fromkeys(lifecycle.CITIES, cutoff),
        },
    )
    return bundle


def test_manifest_rejects_tampering_and_path_escape(registry):
    bundle = make_bundle()
    lifecycle.verify_bundle(bundle.name)
    (bundle / "models/bangkok.pkl").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        lifecycle.verify_bundle(bundle.name)
    for version in ("../escape", "uv-../../escape", "C:/outside", ""):
        with pytest.raises(ValueError, match="identifier"):
            lifecycle.bundle_path(version)


def test_lock_rejects_a_second_writer_and_releases_on_failure(registry):
    with pytest.raises(RuntimeError):
        with lifecycle.deployment_lock():
            with pytest.raises(FileExistsError):
                with lifecycle.deployment_lock():
                    pytest.fail("second writer admitted")
            raise RuntimeError("job failed")
    with lifecycle.deployment_lock():
        pass


def test_gate_rejects_worse_mae_undercalls_and_short_holdout():
    good = lifecycle.score_pair([8.0] * 15, [8.1] * 15)
    baseline = lifecycle.score_pair([8.0] * 15, [8.2] * 15)
    assert lifecycle.gate_scores(good, baseline, baseline)
    assert not lifecycle.gate_scores(baseline, good, good)
    undercall = lifecycle.score_pair([8.0] * 15, [7.95] * 15)
    assert not lifecycle.gate_scores(undercall, good, baseline)
    short = lifecycle.score_pair([8.0] * 13, [8.0] * 13)
    assert not lifecycle.gate_scores(short, short, short)
    with pytest.raises(ValueError, match="Invalid"):
        lifecycle.score_pair([float("nan")], [8.0])


def test_delayed_labels_first_forecast_and_alert(registry):
    day = date(2026, 10, 1)
    series = {c: ([day - timedelta(days=1)], [8.0]) for c in lifecycle.CITIES}
    snapshot = {
        "generated_at": datetime(2026, 10, 1, 1, tzinfo=UTC).isoformat(),
        "cities": {
            c: {
                "data_date": "2026-09-30",
                "model_version": "uv-test",
                "days": [{"date": "2026-10-01", "uv_index_clear_sky": 4.0}],
            }
            for c in lifecycle.CITIES
        },
    }
    lifecycle.record_forecasts(snapshot, series)
    snapshot["cities"]["bangkok"]["days"][0]["uv_index_clear_sky"] = 8.0
    lifecycle.record_forecasts(snapshot, series)
    archive = lifecycle.read_json(lifecycle.ARTIFACTS / "forecast_history.json")
    assert archive["bangkok/2026-10-01/1/uv-test"]["prediction"] == 4.0
    now = datetime(2026, 10, 2, 1, tzinfo=UTC)
    assert lifecycle.monitor(series, now)["status"] == "collecting"
    observed = {c: ([day], [8.0]) for c in lifecycle.CITIES}
    report = lifecycle.monitor(observed, now)
    assert report["scores"]["bangkok/h1/uv-test"]["mae"] == 4.0
    # Revised labels are detected rather than silently replacing prior truth.
    observed["bangkok"] = ([day], [9.0])
    assert lifecycle.monitor(observed, now)["label_corrections"] == ["bangkok/2026-10-01"]
    # Already observed targets cannot be backfilled as a forecast.
    lifecycle.record_forecasts(snapshot, observed)
    assert len(lifecycle.read_json(lifecycle.ARTIFACTS / "forecast_history.json")) == 3


def test_monitor_alert_needs_enough_pairs(registry):
    lifecycle.atomic_json(lifecycle.MODELS / "active.json", {"active": "uv-test", "history": []})
    days = [date(2026, 9, 16) + timedelta(days=i) for i in range(15)]
    records = {
        str(d): {
            "city": "bangkok",
            "target": d.isoformat(),
            "horizon": 1,
            "version": "uv-test",
            "prediction": 4.0,
        }
        for d in days
    }
    lifecycle.atomic_json(lifecycle.ARTIFACTS / "forecast_history.json", records)
    series = {c: (days, [8.0] * 15) for c in lifecycle.CITIES}
    report = lifecycle.monitor(series, datetime(2026, 10, 1, tzinfo=UTC))
    assert report["status"] == "alert"
    assert report["alerts"] == ["bangkok/h1/uv-test"]


def test_pipeline_refuses_leaked_or_insufficient_holdout(registry):
    make_bundle(cutoff="2026-10-01")
    lifecycle.atomic_json(lifecycle.MODELS / "active.json", {"active": "uv-test", "history": []})
    with train_uv_model.DATA.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "city", "uv_index_clear_sky"])
        for c in lifecycle.CITIES:
            writer.writerow(["2026-10-01", c, 8.0])
            writer.writerow(["2026-10-02", c, 8.0])
    with pytest.raises(ValueError, match="15 new"):
        uv_mlops.pipeline(refresh_data=False)
    assert lifecycle.deployment()["active"] == "uv-test"


def passing_gate(bundle, base):
    score = lifecycle.score_pair([8.0] * 15, [8.0] * 15)
    gate = {
        "passed": True,
        "base_version": base,
        "source_sha256": lifecycle.read_json(bundle / "manifest.json")["source_sha256"],
        "manifest_sha256": lifecycle.digest(bundle / "manifest.json"),
        "evaluation_sha256": lifecycle.digest(bundle / "artifacts/evaluation.json"),
        "cities": {
            c: {
                h: {"candidate": score, "incumbent": score, "persistence": score}
                for h in ("h1", "h2")
            }
            for c in lifecycle.CITIES
        },
    }
    lifecycle.atomic_json(bundle / "gate.json", gate)
    lifecycle.atomic_json(bundle / "tracking.json", {"run_id": "offline-test"})


def test_promotion_and_rollback_preflight_preserve_active_on_failure(registry, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from scripts import refresh_uv_forecast

    for version in ("uv-old", "uv-new"):
        bundle = make_bundle(version)
        lifecycle.atomic_json(bundle / "artifacts/evaluation.json", {})
    passing_gate(lifecycle.bundle_path("uv-new"), "uv-old")
    lifecycle.atomic_json(lifecycle.MODELS / "active.json", {"active": "uv-old", "history": []})
    monkeypatch.setattr(lifecycle, "read_csv_observations", lambda _: {})
    monkeypatch.setattr(lifecycle, "record_forecasts", lambda *args: None)
    monkeypatch.setattr(lifecycle, "monitor", lambda *args: None)
    monkeypatch.setattr(
        refresh_uv_forecast,
        "build_snapshot",
        lambda *args, **kwargs: {
            "cities": {"bangkok": {"days": [{"uv_index_clear_sky": float("nan")}]}}
        },
    )
    with pytest.raises(ValueError, match="preflight"):
        uv_mlops.promote("uv-new", "operator")
    assert lifecycle.deployment()["active"] == "uv-old"
    monkeypatch.setattr(
        refresh_uv_forecast,
        "build_snapshot",
        lambda *args, **kwargs: {
            "cities": {c: {"days": [{"uv_index_clear_sky": 8.0}]} for c in lifecycle.CITIES}
        },
    )
    uv_mlops.promote("uv-new", "operator")
    assert lifecycle.deployment()["active"] == "uv-new"
    uv_mlops.rollback("operator")
    state = lifecycle.deployment()
    assert state["active"] == "uv-old"
    assert [h["action"] for h in state["history"]] == ["promote", "rollback"]
    # A gate evaluated against the old deployment cannot promote after another change.
    passing_gate(lifecycle.bundle_path("uv-new"), "uv-stale")
    with pytest.raises(ValueError, match="changed"):
        uv_mlops.promote("uv-new", "operator")
    assert lifecycle.deployment()["active"] == "uv-old"


def test_common_holdout_compares_both_horizons_without_refitting_incumbent(registry, monkeypatch):
    incumbent = make_bundle("uv-incumbent", cutoff="2026-01-01")
    candidate = make_bundle("uv-candidate", cutoff="2026-01-20")
    lifecycle.atomic_json(candidate / "artifacts/metrics.json", {"source_sha256": "test"})
    lifecycle.atomic_json(candidate / "artifacts/evaluation.json", {})
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(21)]
    series = {c: (days, [8.0] * len(days)) for c in lifecycle.CITIES}
    with (candidate / "artifacts/backtest_predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["city", "split", "date", "sarimax_h1", "sarimax_h2"])
        for city in lifecycle.CITIES:
            for offset, day in enumerate(days[1:]):
                writer.writerow([city, "test", day.isoformat(), 8.0, 8.0 if offset else ""])

    class Incumbent:
        def apply(self, observations, *, exog, refit):
            assert not refit and observations.tolist() == [8.0]
            return self

        def get_forecast(self, **kwargs):
            return SimpleNamespace(predicted_mean=np.array([8.1, 8.1]))

        def extend(self, *args, **kwargs):
            return self

    monkeypatch.setattr(uv_mlops.SARIMAXResults, "load", lambda _: Incumbent())
    gate = uv_mlops.gate_candidate(candidate, series, incumbent.name)
    assert gate["passed"]
    assert gate["cities"]["bangkok"]["h1"]["candidate"]["n"] == 20
    assert gate["cities"]["bangkok"]["h2"]["candidate"]["n"] == 19
    manifest = lifecycle.read_json(incumbent / "manifest.json")
    manifest["trained_through"] = dict.fromkeys(lifecycle.CITIES, "2026-01-02")
    lifecycle.atomic_json(incumbent / "manifest.json", manifest)
    with pytest.raises(ValueError, match="holdout labels"):
        uv_mlops.gate_candidate(candidate, series, incumbent.name)


def test_training_produces_isolated_candidate(registry, monkeypatch):
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(60)]
    values = [8.0] * len(days)
    monkeypatch.setattr(
        train_uv_model, "load_data", lambda _: {c: (days, values) for c in lifecycle.CITIES}
    )
    monkeypatch.setattr(train_uv_model, "seasonal_baseline", lambda d, v, a, b: np.array(v[a:b]))

    class State:
        def get_forecast(self, **kwargs):
            return SimpleNamespace(predicted_mean=np.array([8.0, 8.0]))

        def extend(self, *args, **kwargs):
            return self

        def save(self, path):
            path.write_bytes(b"candidate")

    monkeypatch.setattr(train_uv_model, "fit_model", lambda *args: State())

    def no_git(*args, **kwargs):
        raise FileNotFoundError("Git omitted from runtime image")

    monkeypatch.setattr(train_uv_model.subprocess, "run", no_git)
    train_uv_model.DATA.write_text("immutable input", encoding="utf-8")
    lifecycle.MODELS.mkdir()
    live = lifecycle.MODELS / "bangkok.pkl"
    live.write_bytes(b"serving")
    output = lifecycle.bundle_path("uv-training-test")
    train_uv_model.main(
        data_path=train_uv_model.DATA,
        output_dir=output,
        train_end=days[19],
        valid_end=days[39],
        production_end=days[-2],
    )
    assert live.read_bytes() == b"serving"
    _, manifest = lifecycle.verify_bundle(output.name)
    assert manifest["trained_through"]["bangkok"] == days[-2].isoformat()
    assert manifest["git_revision"] == "unknown"
    assert (output / "artifacts/backtest_predictions.csv").exists()
    with pytest.raises(FileExistsError):
        train_uv_model.main(data_path=train_uv_model.DATA, output_dir=output)


def test_pipeline_tracks_candidate_in_real_local_mlflow(registry, monkeypatch):
    make_bundle("uv-incumbent", cutoff="2026-01-01")
    lifecycle.atomic_json(
        lifecycle.MODELS / "active.json",
        {
            "active": "uv-incumbent",
            "history": [],
        },
    )
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(21)]
    with train_uv_model.DATA.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["city", "date", "uv_index_clear_sky"])
        for city in lifecycle.CITIES:
            for day in days:
                writer.writerow([city, day.isoformat(), 8.0])

    def train(**kwargs):
        assert kwargs["valid_end"] == days[0]
        bundle = make_bundle(kwargs["output_dir"].name)
        shutil_source = train_uv_model.DATA.read_bytes()
        (bundle / "dataset.csv").write_bytes(shutil_source)
        lifecycle.atomic_json(
            bundle / "artifacts/metrics.json",
            {
                "source_sha256": lifecycle.digest(bundle / "dataset.csv"),
            },
        )
        with (bundle / "artifacts/backtest_predictions.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(["city", "split", "date", "sarimax_h1", "sarimax_h2"])
            for city in lifecycle.CITIES:
                for i, day in enumerate(days[1:]):
                    writer.writerow([city, "test", day.isoformat(), 8.0, 8.0 if i else ""])
        lifecycle.seal_bundle(
            bundle,
            {
                "source_sha256": lifecycle.digest(bundle / "dataset.csv"),
                "trained_through": dict.fromkeys(lifecycle.CITIES, days[-1].isoformat()),
            },
        )
        return bundle

    class Incumbent:
        def apply(self, *args, **kwargs):
            return self

        def get_forecast(self, **kwargs):
            return SimpleNamespace(predicted_mean=np.array([8.1, 8.1]))

        def extend(self, *args, **kwargs):
            return self

    monkeypatch.setattr(uv_mlops.SARIMAXResults, "load", lambda _: Incumbent())
    monkeypatch.setattr(train_uv_model, "main", train)
    monkeypatch.setattr(
        uv_mlops.evaluate_uv_model,
        "main",
        lambda bundle: lifecycle.atomic_json(
            bundle / "artifacts/evaluation.json", {"test": "pipeline integration"}
        ),
    )
    uri = (registry / "mlruns").as_uri()
    bundle = uv_mlops.pipeline(uri, refresh_data=False)
    assert lifecycle.read_json(bundle / "gate.json")["passed"]
    run_id = lifecycle.read_json(bundle / "tracking.json")["run_id"]
    from mlflow.tracking import MlflowClient

    run = MlflowClient(tracking_uri=uri).get_run(run_id)
    assert run.info.status == "FINISHED"
    assert run.data.metrics["bangkok_h2_mae"] == 0.0
    assert lifecycle.deployment()["active"] == "uv-incumbent"


def test_serving_rejects_snapshot_during_incomplete_version_switch(registry, monkeypatch):
    from backend.services import uv_service

    path = registry / "snapshot.json"
    monkeypatch.setattr(uv_service, "SNAPSHOT", path)
    lifecycle.atomic_json(
        path,
        {
            "generated_at": "2026-10-02T08:00:00+00:00",
            "source": "test",
            "cities": {
                "bangkok": {
                    "data_date": "2026-10-01",
                    "model_version": "uv-old",
                    "days": [
                        {
                            "date": d,
                            "uv_index_clear_sky": 8.0,
                            "value_kind": "SARIMAX forecast",
                            "weather": None,
                        }
                        for d in ("2026-10-02", "2026-10-03")
                    ],
                }
            },
        },
    )
    lifecycle.atomic_json(registry / "serving_version.json", {"version": "uv-new"})
    now = datetime(2026, 10, 2, 9, tzinfo=UTC)
    with pytest.raises(ValueError, match="invalid"):
        uv_service.load_recommendation("bangkok", now)
    lifecycle.atomic_json(registry / "serving_version.json", {"version": "uv-old"})
    assert uv_service.load_recommendation("bangkok", now)["model_version"] == "uv-old"
