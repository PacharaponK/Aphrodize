"""Backtest and locally train clear-sky UV SARIMAX models for three cities."""

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import numpy as np
import statsmodels
from statsmodels.tsa.statespace.sarimax import SARIMAX

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "storage/data/uv/temis_clear_sky_uv.csv"
ARTIFACTS = ROOT / "storage/artifacts/uv"
MODELS = ROOT / "storage/models/uv"
CITIES = ("bangkok", "songkhla", "chiang_mai")
ORDERS = ((1, 0, 0), (2, 0, 0), (3, 0, 0), (1, 0, 1))
TRAIN_END = date(2023, 12, 31)
VALID_END = date(2024, 12, 31)


def load_data(data_path=None):
    series = {city: ([], []) for city in CITIES}
    with (data_path or DATA).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            city = row["city"]
            if city not in series:
                raise ValueError(f"Unknown city: {city}")
            day = date.fromisoformat(row["date"])
            if not row["uv_index_clear_sky"]:
                raise ValueError(f"Missing UV value: {city} {day}; resolve before training")
            uv = float(row["uv_index_clear_sky"])
            if not math.isfinite(uv) or uv < 0:
                raise ValueError(f"Invalid UV value: {city} {day}")
            days, values = series[city]
            if days and day != days[-1] + timedelta(days=1):
                raise ValueError(f"Nonconsecutive date: {city} {day}")
            days.append(day)
            values.append(uv)
    for city, (days, _) in series.items():
        if not days or days[0] > TRAIN_END or days[-1] <= VALID_END:
            raise ValueError(f"Insufficient date range: {city}")
    return series


def fourier(days):
    elapsed = np.array([day.toordinal() - date(2000, 1, 1).toordinal() for day in days])
    return np.column_stack(
        [
            function(2 * np.pi * harmonic * elapsed / 365.2425)
            for harmonic in (1, 2)
            for function in (np.sin, np.cos)
        ]
    )


def fit_model(values, features, order):
    result = SARIMAX(values, exog=features, order=order, trend="c", enforce_stationarity=True).fit(
        disp=False, maxiter=100
    )
    if not result.mle_retvals.get("converged"):
        raise RuntimeError("SARIMAX optimization did not converge")
    return result


def rolling_forecasts(result, days, values, features, start, stop):
    """Each prediction uses only observations through its forecast origin."""
    one_day = np.empty(stop - start)
    two_days = np.full(stop - start, np.nan)
    for offset, index in enumerate(range(start, stop)):
        future = (days[index], days[index] + timedelta(days=1))
        predicted = result.get_forecast(steps=2, exog=fourier(future)).predicted_mean
        one_day[offset] = predicted[0]
        if offset + 1 < len(two_days):
            two_days[offset + 1] = predicted[1]
        result = result.extend(values[index : index + 1], exog=features[index : index + 1])
    return one_day, two_days


def seasonal_baseline(days, values, start, stop):
    known = dict(zip(days, values, strict=True))
    predicted = []
    for day in days[start:stop]:
        try:
            previous_year = day.replace(year=day.year - 1)
        except ValueError:  # 29 February
            previous_year = day.replace(year=day.year - 1, day=28)
        predicted.append(known[previous_year])
    return np.array(predicted)


def score(actual, predicted):
    mask = np.isfinite(predicted)
    error = actual[mask] - predicted[mask]
    return {
        "n": int(mask.sum()),
        "mae": round(float(np.mean(np.abs(error))), 4),
        "rmse": round(float(np.sqrt(np.mean(error**2))), 4),
    }


def main(
    *,
    data_path=DATA,
    output_dir=None,
    train_end=TRAIN_END,
    valid_end=VALID_END,
    production_end=None,
):
    """Train an isolated candidate; never replace the serving model files."""
    output_dir = output_dir or MODELS / "versions" / (
        "uv-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    frozen_data = output_dir / "dataset.csv"
    shutil.copyfile(data_path, frozen_data)
    series = load_data(frozen_data)
    model_dir, artifact_dir = output_dir / "models", output_dir / "artifacts"
    model_dir.mkdir()
    artifact_dir.mkdir()
    data_hash = hashlib.sha256(frozen_data.read_bytes()).hexdigest()
    summary = {
        "source_sha256": data_hash,
        "model": "SARIMAX + 2 annual Fourier harmonics",
        "selection_metric": "validation two-day MAE",
        "statsmodels": statsmodels.__version__,
        "cities": {},
    }
    predictions = []

    for city, (days, raw_values) in series.items():
        values = np.asarray(raw_values)
        features = fourier(days)
        train_stop = next(i for i, day in enumerate(days) if day > train_end)
        valid_stop = next(i for i, day in enumerate(days) if day > valid_end)
        if not 0 < train_stop < valid_stop < len(days):
            raise ValueError("Training, validation and test periods must be nonempty")
        candidates = {}
        selected = None
        for order in ORDERS:
            fitted = fit_model(values[:train_stop], features[:train_stop], order)
            one_day, two_days = rolling_forecasts(
                fitted, days, values, features, train_stop, valid_stop
            )
            key = str(order)
            candidates[key] = score(values[train_stop:valid_stop], two_days)
            exact_mae = float(np.mean(np.abs(values[train_stop + 1 : valid_stop] - two_days[1:])))
            if selected is None or exact_mae < selected[3]:
                selected = (order, one_day, two_days, exact_mae)
        order, valid_one_day, valid_two_days, _ = selected
        city_scores = {"selected_order": list(order), "validation_candidates": candidates}

        for split, start, stop in (
            ("validation", train_stop, valid_stop),
            ("test", valid_stop, len(days)),
        ):
            if split == "validation":
                one_day, two_days = valid_one_day, valid_two_days
            else:
                fitted = fit_model(values[:start], features[:start], order)
                one_day, two_days = rolling_forecasts(fitted, days, values, features, start, stop)
            actual = values[start:stop]
            seasonal = seasonal_baseline(days, values, start, stop)
            persistence = values[start - 1 : stop - 1]
            persistence_two = values[start - 1 : stop - 1].copy()
            persistence_two[1:] = values[start - 1 : stop - 2]
            persistence_two[0] = np.nan
            city_scores[split] = {
                "sarimax_h1": score(actual, one_day),
                "sarimax_h2": score(actual, two_days),
                "seasonal_naive": score(actual, seasonal),
                "persistence_h1": score(actual, persistence),
                "persistence_h2": score(actual, persistence_two),
            }
            for index, day in enumerate(days[start:stop]):
                predictions.append(
                    (
                        city,
                        split,
                        day.isoformat(),
                        actual[index],
                        one_day[index],
                        two_days[index] if index else "",
                        seasonal[index],
                        persistence[index],
                        persistence_two[index] if index else "",
                    )
                )

        final_stop = sum(day <= production_end for day in days) if production_end else len(days)
        final = fit_model(values[:final_stop], features[:final_stop], order)
        final.save(model_dir / f"{city}.pkl")
        city_scores["trained_through"] = days[final_stop - 1].isoformat()
        future_days = (
            days[final_stop - 1] + timedelta(days=1),
            days[final_stop - 1] + timedelta(days=2),
        )
        future_values = final.get_forecast(steps=2, exog=fourier(future_days)).predicted_mean
        city_scores["next_two_days_clear_sky"] = {
            day.isoformat(): round(float(value), 3)
            for day, value in zip(future_days, future_values, strict=True)
        }
        summary["cities"][city] = city_scores
        print(
            f"{city}: selected {order}, validation h2 MAE "
            f"{city_scores['validation']['sarimax_h2']['mae']}, "
            f"test h2 MAE {city_scores['test']['sarimax_h2']['mae']}"
        )

    (artifact_dir / "metrics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (artifact_dir / "backtest_predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            (
                "city",
                "split",
                "date",
                "actual",
                "sarimax_h1",
                "sarimax_h2",
                "seasonal_naive",
                "persistence_h1",
                "persistence_h2",
            )
        )
        writer.writerows(predictions)
    from backend.services.uv_lifecycle import seal_bundle

    try:
        revision = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
            ).stdout.strip()
            or "unknown"
        )
    except OSError:
        revision = "unknown"  # Runtime images can omit Git; source checksums remain recorded.
    seal_bundle(
        output_dir,
        {
            "created_at": datetime.now(UTC).isoformat(),
            "git_revision": revision,
            "source_sha256": data_hash,
            "statsmodels": statsmodels.__version__,
            "train_end": train_end.isoformat(),
            "validation_end": valid_end.isoformat(),
            "trained_through": {c: v["trained_through"] for c, v in summary["cities"].items()},
            "code_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in (
                    "scripts/train_uv_model.py",
                    "scripts/evaluate_uv_model.py",
                    "scripts/uv_mlops.py",
                    "backend/services/uv_lifecycle.py",
                )
            },
        },
    )
    print(f"Candidate saved to {output_dir}; serving version unchanged")
    return output_dir


if __name__ == "__main__":
    main()
