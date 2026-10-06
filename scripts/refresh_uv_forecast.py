"""Refresh public TEMIS data and publish a two-day, locally modeled UV snapshot."""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import numpy as np
from prepare_uv_dataset import main as download_temis
from statsmodels.tsa.statespace.sarimax import SARIMAXResults
from train_uv_model import ARTIFACTS, CITIES, fourier, load_data

from backend.services.uv_lifecycle import (
    atomic_json,
    deployment_lock,
    monitor,
    record_forecasts,
    serving_models,
)
from backend.services.uv_map_service import refresh_api_map

COORDINATES = {
    "bangkok": (13.7563, 100.5018),
    "songkhla": (7.1988, 100.5951),
    "chiang_mai": (18.7883, 98.9853),
}
SNAPSHOT = ARTIFACTS / "forecast_snapshot.json"


def noon_weather(city: str, today) -> dict:
    latitude, longitude = COORDINATES[city]
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "cloud_cover,precipitation_probability",
            "timezone": "Asia/Bangkok",
            "forecast_days": 2,
        }
    )
    try:
        with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=12) as response:
            hourly = json.load(response)["hourly"]
        return {
            day.isoformat(): {
                "cloud_cover_percent": hourly["cloud_cover"][hourly["time"].index(f"{day}T12:00")],
                "rain_probability_percent": hourly["precipitation_probability"][
                    hourly["time"].index(f"{day}T12:00")
                ],
            }
            for day in (today, today + timedelta(days=1))
        }
    except (OSError, ValueError, KeyError, IndexError) as error:
        print(f"{city}: weather unavailable ({type(error).__name__})")
        return {}


def build_snapshot(series, today, *, model_dir=None, version=None):
    if model_dir is None:
        model_dir, version = serving_models()
    if any(series[city][0][-1] < today - timedelta(days=1) for city in CITIES):
        raise ValueError("TEMIS data are older than yesterday; refusing to publish stale UV")
    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "timezone": "Asia/Bangkok",
        "source": "TEMIS UVIEF clear-sky at local solar noon",
        "cities": {},
    }
    for city in CITIES:
        days, values = series[city]
        model_path = model_dir / f"{city}.pkl"
        model = SARIMAXResults.load(model_path)
        if model.nobs > len(days):
            raise ValueError(f"{city}: saved model is newer than TEMIS data")
        if not np.allclose(np.asarray(model.model.endog).ravel(), values[: model.nobs]):
            raise ValueError(f"{city}: TEMIS history changed; retrain before publishing")
        if model.nobs < len(days):
            new_days = days[model.nobs :]
            model = model.append(
                np.asarray(values[model.nobs :]), exog=fourier(new_days), refit=False
            )
        # Keep today's map value a prediction, even when TEMIS already publishes today.
        if days[-1] >= today:
            history_end = days.index(today)
            model = model.apply(
                np.asarray(values[:history_end]), exog=fourier(days[:history_end]), refit=False
            )
            days, values = days[:history_end], values[:history_end]
        forecast_days = [day for day in (today, today + timedelta(days=1)) if day > days[-1]]
        if len(forecast_days) > 2:
            raise ValueError(f"{city}: forecast horizon exceeds evaluated two days")
        predicted = (
            model.get_forecast(steps=len(forecast_days), exog=fourier(forecast_days)).predicted_mean
            if forecast_days
            else []
        )
        forecasts = dict(zip(forecast_days, predicted, strict=True))
        weather = noon_weather(city, today)
        result["cities"][city] = {
            "data_date": days[-1].isoformat(),
            "model_version": version,
            "days": [
                {
                    "date": day.isoformat(),
                    "uv_index_clear_sky": round(
                        float(values[days.index(day)] if day <= days[-1] else forecasts[day]), 2
                    ),
                    "value_kind": "TEMIS satellite estimate"
                    if day <= days[-1]
                    else "SARIMAX forecast",
                    "weather": weather.get(day.isoformat()),
                }
                for day in (today, today + timedelta(days=1))
            ],
        }
    return result


def refresh():
    today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    try:
        map_failures = refresh_api_map(today)
    except (OSError, ValueError, TypeError) as error:
        print(f"UV map snapshot unavailable ({type(error).__name__})")
        map_failures = 1
    download_temis()
    model_dir, _ = serving_models()
    if any(not (model_dir / f"{city}.pkl").exists() for city in CITIES):
        raise ValueError("UV models missing; train, evaluate and approve a candidate first")
    series = load_data()
    snapshot = build_snapshot(series, today)
    record_forecasts(snapshot, series)
    monitoring = monitor(series)
    if monitoring["status"] == "alert":
        print(
            f"UV quality alert: {monitoring['alerts']}; labels: {monitoring['label_corrections']}"
        )
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    version = next(iter(snapshot["cities"].values()))["model_version"]
    atomic_json(ARTIFACTS / "serving_version.json", {"version": version})
    temporary.replace(SNAPSHOT)
    print(f"Published {SNAPSHOT} for {today} and {today + timedelta(days=1)}")
    if map_failures:
        raise RuntimeError("Some UV map batches failed; retry refresh in 30 minutes")


def main():
    with deployment_lock():
        refresh()


if __name__ == "__main__":
    main()
