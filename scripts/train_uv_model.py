"""Backtest and locally train clear-sky UV SARIMAX models for three cities."""

import csv
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import statsmodels
from statsmodels.tsa.statespace.sarimax import SARIMAX


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "storage/data/uv/temis_clear_sky_uv.csv"
ARTIFACTS = ROOT / "storage/artifacts/uv"
MODELS = ROOT / "storage/models/uv"
CITIES = ("bangkok", "songkhla", "chiang_mai")
ORDERS = ((1, 0, 0), (2, 0, 0), (3, 0, 0), (1, 0, 1))
TRAIN_END = date(2023, 12, 31)
VALID_END = date(2024, 12, 31)


def load_data():
    series = {city: ([], []) for city in CITIES}
    with DATA.open(newline="", encoding="utf-8") as file:
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
        [function(2 * np.pi * harmonic * elapsed / 365.2425)
         for harmonic in (1, 2) for function in (np.sin, np.cos)]
    )


def fit_model(values, features, order):
    result = SARIMAX(
        values, exog=features, order=order, trend="c", enforce_stationarity=True
    ).fit(disp=False, maxiter=100)
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
        result = result.extend(values[index:index + 1], exog=features[index:index + 1])
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
    return {"n": int(mask.sum()), "mae": round(float(np.mean(np.abs(error))), 4),
            "rmse": round(float(np.sqrt(np.mean(error ** 2))), 4)}


def main():
    series = load_data()
    data_hash = hashlib.sha256(DATA.read_bytes()).hexdigest()
    summary = {"source_sha256": data_hash, "model": "SARIMAX + 2 annual Fourier harmonics",
               "selection_metric": "validation two-day MAE",
               "statsmodels": statsmodels.__version__, "cities": {}}
    predictions = []
    MODELS.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    for city, (days, raw_values) in series.items():
        values = np.asarray(raw_values)
        features = fourier(days)
        train_stop = next(i for i, day in enumerate(days) if day > TRAIN_END)
        valid_stop = next(i for i, day in enumerate(days) if day > VALID_END)
        candidates = {}
        selected = None
        for order in ORDERS:
            fitted = fit_model(values[:train_stop], features[:train_stop], order)
            one_day, two_days = rolling_forecasts(
                fitted, days, values, features, train_stop, valid_stop
            )
            key = str(order)
            candidates[key] = score(values[train_stop:valid_stop], two_days)
            exact_mae = float(np.mean(np.abs(values[train_stop + 1:valid_stop] - two_days[1:])))
            if selected is None or exact_mae < selected[3]:
                selected = (order, one_day, two_days, exact_mae)
        order, valid_one_day, valid_two_days, _ = selected
        city_scores = {"selected_order": list(order), "validation_candidates": candidates}

        for split, start, stop in (("validation", train_stop, valid_stop),
                                   ("test", valid_stop, len(days))):
            if split == "validation":
                one_day, two_days = valid_one_day, valid_two_days
            else:
                fitted = fit_model(values[:start], features[:start], order)
                one_day, two_days = rolling_forecasts(
                    fitted, days, values, features, start, stop
                )
            actual = values[start:stop]
            seasonal = seasonal_baseline(days, values, start, stop)
            persistence = values[start - 1:stop - 1]
            persistence_two = values[start - 1:stop - 1].copy()
            persistence_two[1:] = values[start - 1:stop - 2]
            persistence_two[0] = np.nan
            city_scores[split] = {
                "sarimax_h1": score(actual, one_day),
                "sarimax_h2": score(actual, two_days),
                "seasonal_naive": score(actual, seasonal),
                "persistence_h1": score(actual, persistence),
                "persistence_h2": score(actual, persistence_two),
            }
            for index, day in enumerate(days[start:stop]):
                predictions.append((city, split, day.isoformat(), actual[index], one_day[index],
                                    two_days[index] if index else "", seasonal[index],
                                    persistence[index], persistence_two[index] if index else ""))

        final = fit_model(values, features, order)
        final.save(MODELS / f"{city}.pkl")
        city_scores["trained_through"] = days[-1].isoformat()
        future_days = (days[-1] + timedelta(days=1), days[-1] + timedelta(days=2))
        future_values = final.get_forecast(steps=2, exog=fourier(future_days)).predicted_mean
        city_scores["next_two_days_clear_sky"] = {
            day.isoformat(): round(float(value), 3)
            for day, value in zip(future_days, future_values, strict=True)
        }
        summary["cities"][city] = city_scores
        print(f"{city}: selected {order}, validation h2 MAE "
              f"{city_scores['validation']['sarimax_h2']['mae']}, "
              f"test h2 MAE {city_scores['test']['sarimax_h2']['mae']}")

    (ARTIFACTS / "metrics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (ARTIFACTS / "backtest_predictions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("city", "split", "date", "actual", "sarimax_h1", "sarimax_h2",
                         "seasonal_naive", "persistence_h1", "persistence_h2"))
        writer.writerows(predictions)
    print(f"Saved models to {MODELS} and backtest results to {ARTIFACTS}")


if __name__ == "__main__":
    main()
