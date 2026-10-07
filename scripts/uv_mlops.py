"""UV candidate pipeline and explicit, audited promotion/rollback commands."""

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAXResults

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services import uv_lifecycle as lifecycle  # noqa: E402
from scripts import evaluate_uv_model, train_uv_model  # noqa: E402


class TrainingNotReady(ValueError):
    """There are not enough new labels for a leakage-free comparison."""


def new_version():
    return "uv-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]


def bootstrap(actor):
    """Import the existing model without claiming a new validation or approval."""
    with lifecycle.deployment_lock():
        if lifecycle.deployment()["active"]:
            raise ValueError("UV registry is already initialized")
        metrics = lifecycle.read_json(lifecycle.ARTIFACTS / "metrics.json")
        version = new_version()
        bundle = lifecycle.bundle_path(version)
        (bundle / "models").mkdir(parents=True)
        (bundle / "artifacts").mkdir()
        shutil.copyfile(train_uv_model.DATA, bundle / "dataset.csv")
        for city in lifecycle.CITIES:
            shutil.copyfile(lifecycle.MODELS / f"{city}.pkl", bundle / "models" / f"{city}.pkl")
        shutil.copyfile(lifecycle.ARTIFACTS / "metrics.json", bundle / "artifacts/metrics.json")
        lifecycle.seal_bundle(
            bundle,
            {
                "created_at": datetime.now(UTC).isoformat(),
                "origin": "legacy-import",
                "trained_through": {
                    c: metrics["cities"][c]["trained_through"] for c in lifecycle.CITIES
                },
                "source_sha256": lifecycle.digest(bundle / "dataset.csv"),
                "original_training_sha256": metrics["source_sha256"],
            },
        )
        publish(version, actor, "bootstrap", None)
        return version


def gate_candidate(bundle, series, incumbent_version):
    incumbent_bundle, manifest = lifecycle.verify_bundle(incumbent_version)
    metrics = lifecycle.read_json(bundle / "artifacts/metrics.json")
    with (bundle / "artifacts/backtest_predictions.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    results = {}
    for city in lifecycle.CITIES:
        test_rows = [r for r in rows if r["city"] == city and r["split"] == "test"]
        start_date = date.fromisoformat(test_rows[0]["date"])
        if start_date <= date.fromisoformat(manifest["trained_through"][city]):
            raise ValueError("Incumbent already trained on holdout labels")
        days, raw = series[city]
        start = days.index(start_date)
        incumbent = SARIMAXResults.load(incumbent_bundle / "models" / f"{city}.pkl")
        incumbent = incumbent.apply(
            np.asarray(raw[:start]), exog=train_uv_model.fourier(days[:start]), refit=False
        )
        one, two = train_uv_model.rolling_forecasts(
            incumbent, days, np.asarray(raw), train_uv_model.fourier(days), start, len(days)
        )
        horizons = {}
        for horizon, predictions in ((1, one), (2, two)):
            offset = horizon - 1
            actual = raw[start + offset :]
            candidate = [float(r[f"sarimax_h{horizon}"]) for r in test_rows[offset:]]
            baseline = raw[start + offset - horizon : len(raw) - horizon]
            scores = {
                "candidate": lifecycle.score_pair(actual, candidate),
                "incumbent": lifecycle.score_pair(actual, predictions[offset:].tolist()),
                "persistence": lifecycle.score_pair(actual, baseline),
            }
            scores["passed"] = lifecycle.gate_scores(
                scores["candidate"], scores["incumbent"], scores["persistence"]
            )
            scores["dates"] = [days[start + offset].isoformat(), days[-1].isoformat()]
            horizons[f"h{horizon}"] = scores
        results[city] = horizons
    return {
        "base_version": incumbent_version,
        "cities": results,
        "passed": all(s["passed"] for h in results.values() for s in h.values()),
        "policy": "min 14 pairs per horizon; MAE <= incumbent and persistence; "
        "UV >=8/>=11 undercalls <= incumbent, every city/horizon",
        "source_sha256": metrics["source_sha256"],
        "evaluation_sha256": lifecycle.digest(bundle / "artifacts/evaluation.json"),
        "manifest_sha256": lifecycle.digest(bundle / "manifest.json"),
    }


def pipeline(tracking_uri=None, *, refresh_data=True):
    if refresh_data:
        from scripts.prepare_uv_dataset import main as prepare

        with lifecycle.deployment_lock():
            prepare()
    incumbent_version = lifecycle.deployment()["active"]
    if not incumbent_version:
        raise ValueError("Run bootstrap before the comparison pipeline")
    _, manifest = lifecycle.verify_bundle(incumbent_version)
    series = lifecycle.read_csv_observations(train_uv_model.DATA)
    newest_common = min(days[-1] for days, _ in series.values())
    latest_training = max(date.fromisoformat(v) for v in manifest["trained_through"].values())
    test_start = max(latest_training + timedelta(days=1), newest_common - timedelta(days=89))
    if (newest_common - test_start).days < 14:
        raise TrainingNotReady(
            "Need at least 15 new observed days after incumbent parameter training "
            "for leakage-free h1/h2 comparison; serving version unchanged. "
            f"Earliest test end: {latest_training + timedelta(days=15)}"
        )
    if any(days[-1] != newest_common for days, _ in series.values()):
        raise ValueError("All cities must share the same latest observation date")
    valid_end = test_start - timedelta(days=1)
    today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    bundle = train_uv_model.main(
        output_dir=lifecycle.bundle_path(new_version()),
        train_end=valid_end - timedelta(days=365),
        valid_end=valid_end,
        production_end=today - timedelta(days=1),
    )
    evaluate_uv_model.main(bundle)
    frozen_series = lifecycle.read_csv_observations(bundle / "dataset.csv")
    gate = gate_candidate(bundle, frozen_series, incumbent_version)
    lifecycle.atomic_json(bundle / "gate.json", gate)
    import mlflow

    mlflow.set_tracking_uri(
        tracking_uri
        or os.environ.get("MLFLOW_TRACKING_URI")
        or "http://localhost:5000"
    )
    mlflow.set_experiment("uv-clear-sky")
    with mlflow.start_run(run_name=bundle.name) as run:
        mlflow.log_params(
            {
                "version": bundle.name,
                "base_version": incumbent_version,
                "source_sha256": gate["source_sha256"],
                "train_end": (valid_end - timedelta(days=365)).isoformat(),
                "validation_end": valid_end.isoformat(),
            }
        )
        mlflow.set_tag("gate_passed", gate["passed"])
        for city, horizons in gate["cities"].items():
            for horizon, scores in horizons.items():
                mlflow.log_metric(f"{city}_{horizon}_mae", scores["candidate"]["mae"])
                for role in ("candidate", "incumbent", "persistence"):
                    prefix = f"{city}_{horizon}_{role}"
                    mlflow.log_metrics(
                        {
                            prefix + "_mae": scores[role]["mae"],
                            prefix + "_bias": scores[role]["bias"],
                            **{
                                prefix + "_undercalls_" + t: n
                                for t, n in scores[role]["undercalls"].items()
                            },
                        }
                    )
        mlflow.log_artifacts(str(bundle))
        lifecycle.atomic_json(bundle / "tracking.json", {"run_id": run.info.run_id})
    print(json.dumps({"version": bundle.name, "gate_passed": gate["passed"]}))
    return bundle


def publish(version, actor, action, expected):
    """Caller holds the deployment lock; preflight before changing active.json."""
    if not actor.strip():
        raise ValueError("Approval actor must be recorded")
    state = lifecycle.deployment()
    if state["active"] != expected:
        raise ValueError("Serving version changed; rerun evaluation")
    bundle, _ = lifecycle.verify_bundle(version)
    # Import here to retain compatibility with direct refresh script execution.
    sys.path.insert(0, str(ROOT / "scripts"))
    from scripts.refresh_uv_forecast import build_snapshot

    series = lifecycle.read_csv_observations(train_uv_model.DATA)
    snapshot = build_snapshot(
        series,
        datetime.now(ZoneInfo("Asia/Bangkok")).date(),
        model_dir=bundle / "models",
        version=version,
    )
    for value in snapshot["cities"].values():
        for entry in value["days"]:
            uv = entry["uv_index_clear_sky"]
            if not np.isfinite(uv) or not 0 <= uv <= 25:
                raise ValueError("Deployment forecast preflight failed")
    state["history"].append(
        {
            "from": expected,
            "to": version,
            "actor": actor,
            "action": action,
            "at": datetime.now(UTC).isoformat(),
        }
    )
    state["active"] = version
    lifecycle.atomic_json(lifecycle.ARTIFACTS / "serving_version.json", {"version": version})
    lifecycle.atomic_json(lifecycle.MODELS / "active.json", state)
    # Readers reject mismatched versions if a process dies between these atomic writes.
    lifecycle.atomic_json(lifecycle.ARTIFACTS / "forecast_snapshot.json", snapshot)
    lifecycle.record_forecasts(snapshot, series)
    lifecycle.monitor(series)


def promote(version, actor):
    with lifecycle.deployment_lock():
        bundle, manifest = lifecycle.verify_bundle(version)
        gate = lifecycle.read_json(bundle / "gate.json")
        if (
            gate["passed"] is not True
            or gate["source_sha256"] != manifest["source_sha256"]
            or gate["manifest_sha256"] != lifecycle.digest(bundle / "manifest.json")
            or gate["evaluation_sha256"] != lifecycle.digest(bundle / "artifacts/evaluation.json")
            or not (bundle / "tracking.json").exists()
        ):
            raise ValueError("Candidate has not passed its intact, tracked quality gate")
        if set(gate["cities"]) != set(lifecycle.CITIES) or any(
            set(h) != {"h1", "h2"} for h in gate["cities"].values()
        ):
            raise ValueError("Quality gate must cover every city and horizon")
        if not all(
            lifecycle.gate_scores(s["candidate"], s["incumbent"], s["persistence"])
            for h in gate["cities"].values()
            for s in h.values()
        ):
            raise ValueError("Candidate scores fail the quality gate")
        publish(version, actor, "promote", gate["base_version"])


def rollback(actor):
    with lifecycle.deployment_lock():
        state = lifecycle.deployment()
        if not state["history"] or not state["history"][-1]["from"]:
            raise ValueError("No prior deployment available")
        publish(state["history"][-1]["from"], actor, "rollback", state["active"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("bootstrap", "promote", "rollback"):
        command = sub.add_parser(name)
        command.add_argument("--actor", required=True)
        if name == "promote":
            command.add_argument("version")
    candidate = sub.add_parser("pipeline")
    candidate.add_argument("--tracking-uri")
    candidate.add_argument("--offline", action="store_true", help="Use the existing local CSV")
    sub.add_parser("monitor")
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "bootstrap":
        print(bootstrap(args.actor))
    elif args.command == "pipeline":
        try:
            bundle = pipeline(args.tracking_uri, refresh_data=not args.offline)
        except Exception as error:
            lifecycle.atomic_json(
                lifecycle.ARTIFACTS / "pipeline_status.json",
                {
                    "at": datetime.now(UTC).isoformat(),
                    "status": "not_ready" if isinstance(error, TrainingNotReady) else "failed",
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
            )
            if isinstance(error, TrainingNotReady):
                print(str(error))
                raise SystemExit(2) from None
            raise
        gate_passed = lifecycle.read_json(bundle / "gate.json")["passed"]
        lifecycle.atomic_json(
            lifecycle.ARTIFACTS / "pipeline_status.json",
            {
                "at": datetime.now(UTC).isoformat(),
                "status": "awaiting_review" if gate_passed else "rejected",
                "version": bundle.name,
                "gate_passed": gate_passed,
            },
        )
    elif args.command == "promote":
        promote(args.version, args.actor)
    elif args.command == "rollback":
        rollback(args.actor)
    elif args.command == "monitor":
        with lifecycle.deployment_lock():
            print(
                json.dumps(
                    lifecycle.monitor(lifecycle.read_csv_observations(train_uv_model.DATA)),
                    indent=2,
                )
            )
    else:
        print(json.dumps(lifecycle.deployment(), indent=2))


if __name__ == "__main__":
    main()
