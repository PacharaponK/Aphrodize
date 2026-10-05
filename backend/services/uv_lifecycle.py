"""Local UV version registry, deployment lock and delayed-label monitoring."""

import csv
import hashlib
import json
import math
import re
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "storage/models/uv"
ARTIFACTS = ROOT / "storage/artifacts/uv"
CITIES = ("bangkok", "songkhla", "chiang_mai")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def deployment_lock():
    MODELS.mkdir(parents=True, exist_ok=True)
    lock = MODELS / "deployment.lock"
    # ponytail: one local writer; use distributed leases if deploying on multiple hosts.
    with lock.open("x", encoding="utf-8") as file:
        file.write(datetime.now(UTC).isoformat())
    try:
        yield
    finally:
        lock.unlink()


def bundle_path(version):
    if not isinstance(version, str) or not re.fullmatch(r"uv-[A-Za-z0-9-]{1,80}", version):
        raise ValueError("Invalid UV version identifier")
    path = MODELS / "versions" / version
    if path.resolve().parent != (MODELS / "versions").resolve() or path.is_symlink():
        raise ValueError("UV version must be inside the local registry")
    return path


def seal_bundle(bundle, metadata):
    files = [bundle / "models" / f"{city}.pkl" for city in CITIES]
    files += [bundle / "dataset.csv", bundle / "artifacts/metrics.json"]
    predictions = bundle / "artifacts/backtest_predictions.csv"
    if predictions.exists():
        files.append(predictions)
    atomic_json(
        bundle / "manifest.json",
        {
            **metadata,
            "version": bundle.name,
            "files": {p.relative_to(bundle).as_posix(): digest(p) for p in files},
        },
    )


def verify_bundle(version):
    bundle = bundle_path(version)
    manifest = read_json(bundle / "manifest.json")
    required = {f"models/{c}.pkl" for c in CITIES} | {"dataset.csv", "artifacts/metrics.json"}
    if manifest["version"] != version or not required <= manifest["files"].keys():
        raise ValueError("Incomplete UV manifest")
    for name, checksum in manifest["files"].items():
        path = bundle / name
        if not path.resolve().is_relative_to(bundle.resolve()) or path.is_symlink():
            raise ValueError("Artifact path leaves the version bundle")
        if digest(path) != checksum:
            raise ValueError(f"UV artifact checksum mismatch: {name}")
    if set(manifest["trained_through"]) != set(CITIES):
        raise ValueError("Incomplete UV training cutoff")
    for cutoff in manifest["trained_through"].values():
        date.fromisoformat(cutoff)
    return bundle, manifest


def deployment():
    path = MODELS / "active.json"
    return read_json(path) if path.exists() else {"active": None, "history": []}


def serving_models():
    version = deployment()["active"]
    if version:
        bundle, _ = verify_bundle(version)
        return bundle / "models", version
    return MODELS, "legacy-unregistered"


def score_pair(actual, predicted):
    if not actual or len(actual) != len(predicted):
        raise ValueError("Empty or mismatched UV evaluation pairs")
    if any(not math.isfinite(x) or not 0 <= x <= 25 for x in actual + predicted):
        raise ValueError("Invalid UV evaluation value")
    errors = [p - a for a, p in zip(actual, predicted, strict=True)]
    return {
        "n": len(errors),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "bias": sum(errors) / len(errors),
        # Match serving's continuous UV thresholds, not rounded display values.
        "undercalls": {
            str(t): sum(a >= t and p < t for a, p in zip(actual, predicted, strict=True))
            for t in (8, 11)
        },
    }


def gate_scores(candidate, incumbent, baseline):
    return (
        candidate["n"] >= 14
        and candidate["n"] == incumbent["n"] == baseline["n"]
        and candidate["mae"] <= min(incumbent["mae"], baseline["mae"])
        and all(candidate["undercalls"][t] <= incumbent["undercalls"][t] for t in ("8", "11"))
    )


def record_forecasts(snapshot, series):
    """Keep the first forecast per target/horizon/version; never backfill known labels."""
    archive = ARTIFACTS / "forecast_history.json"
    records = read_json(archive) if archive.exists() else {}
    for city, value in snapshot["cities"].items():
        cutoff = date.fromisoformat(value["data_date"])
        observed_through = series[city][0][-1]
        for day in value["days"]:
            target = date.fromisoformat(day["date"])
            horizon = (target - cutoff).days
            if target <= observed_through or horizon not in (1, 2):
                continue
            key = f"{city}/{target}/{horizon}/{value['model_version']}"
            records.setdefault(
                key,
                {
                    "city": city,
                    "target": target.isoformat(),
                    "horizon": horizon,
                    "version": value["model_version"],
                    "generated_at": snapshot["generated_at"],
                    "prediction": day["uv_index_clear_sky"],
                },
            )
    # ponytail: JSON archive for a 3-city pilot; move to SQL if history exceeds one year.
    cutoff = datetime.fromisoformat(snapshot["generated_at"]).date() - timedelta(days=365)
    records = {k: r for k, r in records.items() if date.fromisoformat(r["target"]) >= cutoff}
    atomic_json(archive, records)


def monitor(series, now=None):
    now = now or datetime.now(UTC)
    archive = ARTIFACTS / "forecast_history.json"
    records = read_json(archive) if archive.exists() else {}
    observations = {c: dict(zip(days, values, strict=True)) for c, (days, values) in series.items()}
    active = deployment()["active"] or "legacy-unregistered"
    groups = {}
    corrections = []
    for record in records.values():
        actual = observations[record["city"]].get(date.fromisoformat(record["target"]))
        if actual is None:
            continue
        if "actual" in record and actual != record["actual"]:
            corrections.append(f"{record['city']}/{record['target']}")
        record.setdefault("actual", actual)
        if date.fromisoformat(record["target"]) < now.date() - timedelta(days=30):
            continue
        key = f"{record['city']}/h{record['horizon']}/{record['version']}"
        group = groups.setdefault(key, ([], []))
        group[0].append(record["actual"])
        group[1].append(record["prediction"])
    scores = {key: score_pair(*pairs) for key, pairs in groups.items()}
    # Initial alert policy; operational thresholds require calibration on collected forecasts.
    alerts = [
        key
        for key, score in scores.items()
        if key.endswith("/" + active)
        and score["n"] >= 14
        and (score["mae"] > 1.0 or abs(score["bias"]) > 0.5)
    ]
    current_scores = [score for key, score in scores.items() if key.endswith("/" + active)]
    report = {
        "generated_at": now.isoformat(),
        "window_days": 30,
        "active": active,
        "status": "alert"
        if alerts or corrections
        else "ok"
        if len(current_scores) == len(CITIES) * 2 and all(s["n"] >= 14 for s in current_scores)
        else "collecting",
        "alerts": alerts,
        "label_corrections": sorted(set(corrections)),
        "scores": scores,
        "policy": {"min_pairs": 14, "mae_alert": 1.0, "absolute_bias_alert": 0.5},
        "drift_scope": "forecast error and bias; not a distribution drift detector",
    }
    atomic_json(archive, records)
    atomic_json(ARTIFACTS / "monitoring.json", report)
    return report


def read_csv_observations(path):
    series = {city: ([], []) for city in CITIES}
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            days, values = series[row["city"]]
            day, value = date.fromisoformat(row["date"]), float(row["uv_index_clear_sky"])
            if not math.isfinite(value) or not 0 <= value <= 25:
                raise ValueError("Invalid TEMIS observation")
            if days and day != days[-1] + timedelta(days=1):
                raise ValueError("TEMIS observations must be consecutive")
            days.append(day)
            values.append(value)
    if any(not days for days, _ in series.values()):
        raise ValueError("Missing TEMIS city")
    return series
