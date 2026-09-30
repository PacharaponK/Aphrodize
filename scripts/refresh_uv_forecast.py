"""Refresh public TEMIS data and publish a two-day, locally modeled UV snapshot."""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import numpy as np
from prepare_uv_dataset import main as download_temis
from statsmodels.tsa.statespace.sarimax import SARIMAXResults
from train_uv_model import ARTIFACTS, CITIES, MODELS, fourier, load_data
from train_uv_model import main as train_models

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


def build_snapshot(series, today):
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
        model_path = MODELS / f"{city}.pkl"
        model = SARIMAXResults.load(model_path)
        if model.nobs > len(days):
            raise ValueError(f"{city}: saved model is newer than TEMIS data")
        if not np.allclose(np.asarray(model.model.endog).ravel(), values[:model.nobs]):
            raise ValueError(f"{city}: TEMIS history changed; retrain before publishing")
        if model.nobs < len(days):
            new_days = days[model.nobs :]
            model = model.append(
                np.asarray(values[model.nobs :]), exog=fourier(new_days), refit=False
            )
            model.save(model_path)
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
            "model_version": f"sarimax-fourier-{model.nobs}",
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


def main():
    download_temis()
    if any(not (MODELS / f"{city}.pkl").exists() for city in CITIES):
        train_models()
    series = load_data()
    today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    snapshot = build_snapshot(series, today)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(SNAPSHOT)
    print(f"Published {SNAPSHOT} for {today} and {today + timedelta(days=1)}")


if __name__ == "__main__":
    main()
