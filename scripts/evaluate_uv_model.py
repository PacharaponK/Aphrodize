"""Audit held-out two-day UV forecasts before using them in the app."""

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "storage/artifacts/uv"
DATA = ROOT / "storage/data/uv/temis_clear_sky_uv.csv"
THRESHOLDS = (8, 11)


def block_bootstrap_ci(improvements, *, block=14, repeats=2000, seed=42):
    """Percentile interval for paired daily MAE gains, retaining short-run dependence."""
    gains = np.asarray(improvements, dtype=float)
    if len(gains) < block:
        raise ValueError("Not enough test days for a block bootstrap")
    rng = np.random.default_rng(seed)
    starts = rng.integers(
        0, len(gains) - block + 1, size=(repeats, (len(gains) + block - 1) // block)
    )
    samples = (starts[:, :, None] + np.arange(block)).reshape(repeats, -1)[:, : len(gains)]
    return [
        round(float(value), 4) for value in np.quantile(gains[samples].mean(axis=1), (0.025, 0.975))
    ]


def threshold_counts(actual, predicted, threshold):
    # Public UV categories use whole-number UVI, so compare displayed values.
    actual_high = np.floor(actual + 0.5) >= threshold
    predicted_high = np.floor(predicted + 0.5) >= threshold
    return {
        "actual_at_or_above": int(actual_high.sum()),
        "undercalled": int((actual_high & ~predicted_high).sum()),
        "false_alarms": int((~actual_high & predicted_high).sum()),
    }


def main(bundle=None):
    artifacts = bundle / "artifacts" if bundle else ARTIFACTS
    data = bundle / "dataset.csv" if bundle else DATA
    metrics = json.loads((artifacts / "metrics.json").read_text(encoding="utf-8"))
    if hashlib.sha256(data.read_bytes()).hexdigest() != metrics["source_sha256"]:
        raise ValueError("Training CSV changed; rerun train_uv_model.py first")

    grouped = defaultdict(list)
    with (artifacts / "backtest_predictions.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row["split"] == "test" and row["sarimax_h2"]:
                grouped[row["city"]].append(row)
    if set(grouped) != set(metrics["cities"]):
        raise ValueError("Prediction cities do not match training metrics")

    report = {
        "horizon_days": 2,
        "split": "test",
        "bootstrap_block_days": 14,
        "bootstrap_repeats": 2000,
        "cities": {},
    }
    for city, rows in grouped.items():
        days = [date.fromisoformat(row["date"]) for row in rows]
        if len(set(days)) != len(days) or days != sorted(days):
            raise ValueError(f"Duplicate or unsorted test dates: {city}")
        actual = np.array([float(row["actual"]) for row in rows])
        model = np.array([float(row["sarimax_h2"]) for row in rows])
        baseline = np.array([float(row["persistence_h2"]) for row in rows])
        if not np.isfinite(np.column_stack((actual, model, baseline))).all():
            raise ValueError(f"Nonfinite test value: {city}")

        absolute_error = np.abs(model - actual)
        baseline_error = np.abs(baseline - actual)
        mae = float(absolute_error.mean())
        saved = metrics["cities"][city]["test"]["sarimax_h2"]
        if len(rows) != saved["n"] or round(mae, 4) != saved["mae"]:
            raise ValueError(f"Backtest rows disagree with metrics: {city}")
        by_year = {}
        by_month = {}
        for label, groups in (
            (by_year, [day.year for day in days]),
            (by_month, [day.month for day in days]),
        ):
            for key in sorted(set(groups)):
                mask = np.array([group == key for group in groups])
                label[str(key)] = {
                    "n": int(mask.sum()),
                    "model_mae": round(float(absolute_error[mask].mean()), 4),
                    "persistence_mae": round(float(baseline_error[mask].mean()), 4),
                }

        city_report = {
            "n": len(rows),
            "dates": [days[0].isoformat(), days[-1].isoformat()],
            "mae": round(mae, 4),
            "rmse": round(float(np.sqrt(np.mean((model - actual) ** 2))), 4),
            "bias_predicted_minus_actual": round(float(np.mean(model - actual)), 4),
            "p90_absolute_error": round(float(np.quantile(absolute_error, 0.9)), 4),
            "max_absolute_error": round(float(absolute_error.max()), 4),
            "persistence_mae": round(float(baseline_error.mean()), 4),
            "mae_gain_over_persistence": round(float((baseline_error - absolute_error).mean()), 4),
            "mae_gain_95pct_block_bootstrap_ci": block_bootstrap_ci(
                baseline_error - absolute_error
            ),
            "months_beating_persistence": sum(
                item["model_mae"] < item["persistence_mae"] for item in by_month.values()
            ),
            "by_year": by_year,
            "by_month": by_month,
            "thresholds": {
                str(threshold): threshold_counts(actual, model, threshold)
                for threshold in THRESHOLDS
            },
        }
        report["cities"][city] = city_report
        print(
            f"{city}: MAE {city_report['mae']}, gain 95% CI "
            f"{city_report['mae_gain_95pct_block_bootstrap_ci']}, "
            f"months beating persistence {city_report['months_beating_persistence']}/12"
        )

    output = artifacts / "evaluation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {output}")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    main(parser.parse_args().bundle)
