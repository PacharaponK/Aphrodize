"""Account-isolated, one-day forecasts for directly reported daily metrics."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from statistics import fmean
from uuid import UUID

from backend.core.db.models import DailyHealthEntry

PERSONAL_FORECAST_MODEL_ID = "account-personal-linear-trend-v1"
PERSONAL_FORECAST_HISTORY_DAYS = 7
PERSONAL_FORECAST_MINIMUM_OBSERVATIONS = 3


def build_personal_daily_health_forecast(
    entries: Iterable[DailyHealthEntry],
    *,
    user_id: UUID,
    as_of_date: date,
) -> dict:
    """Build a one-day linear trend from this account's real entries only.

    Imported, fixture, synthetic, other-account, and future rows are excluded even if
    a caller accidentally supplies them. The output contains a seven-calendar-day
    actual series, leaving missing dates empty rather than treating them as zero.
    """
    window_start = as_of_date - timedelta(days=PERSONAL_FORECAST_HISTORY_DAYS - 1)
    target_date = as_of_date + timedelta(days=1)
    actual_by_date: dict[date, DailyHealthEntry] = {}

    for entry in entries:
        if (
            entry.user_id == user_id
            and entry.data_source == "user_reported"
            and window_start <= entry.local_date <= as_of_date
        ):
            actual_by_date[entry.local_date] = entry

    actual = []
    for day_offset in range(PERSONAL_FORECAST_HISTORY_DAYS):
        local_date = window_start + timedelta(days=day_offset)
        entry = actual_by_date.get(local_date)
        actual.append(
            {
                "local_date": local_date.isoformat(),
                "sleep_duration_minutes": (
                    entry.sleep_duration_minutes if entry is not None else None
                ),
                "water_intake_ml": entry.water_intake_ml if entry is not None else None,
            }
        )

    observed = [point for point in actual if point["sleep_duration_minutes"] is not None]
    predictions = {
        "sleep_duration_minutes": _forecast_metric(
            actual,
            metric="sleep_duration_minutes",
            target_offset=PERSONAL_FORECAST_HISTORY_DAYS,
            maximum=600,
        ),
        "water_intake_ml": _forecast_metric(
            actual,
            metric="water_intake_ml",
            target_offset=PERSONAL_FORECAST_HISTORY_DAYS,
            maximum=20_000,
        ),
    }
    status = (
        "forecasted"
        if all(item["status"] == "predicted" for item in predictions.values())
        else "insufficient_history"
    )

    return {
        "status": status,
        "prediction_target_date": target_date.isoformat(),
        "history_start_date": window_start.isoformat(),
        "history_end_date": as_of_date.isoformat(),
        "actual": actual,
        "predictions": predictions,
        "model": {
            "model_id": PERSONAL_FORECAST_MODEL_ID,
            "family": "personal_time_series_linear_trend",
            "scope": "account_only",
            "prediction_horizon_days": 1,
            "history_window_days": PERSONAL_FORECAST_HISTORY_DAYS,
            "observations_used": len(observed),
            "minimum_observations": PERSONAL_FORECAST_MINIMUM_OBSERVATIONS,
            "method": "ordinary_least_squares_on_actual_calendar_day_values",
        },
    }


def _forecast_metric(
    actual: list[dict],
    *,
    metric: str,
    target_offset: int,
    maximum: int,
) -> dict[str, int | str | None]:
    observations = [
        (index, point[metric])
        for index, point in enumerate(actual)
        if isinstance(point[metric], int)
    ]
    if len(observations) < PERSONAL_FORECAST_MINIMUM_OBSERVATIONS:
        return {"value": None, "status": "insufficient_history"}

    x_values = [float(index) for index, _ in observations]
    y_values = [float(value) for _, value in observations]
    x_mean = fmean(x_values)
    y_mean = fmean(y_values)
    variance = sum((x - x_mean) ** 2 for x in x_values)
    if variance == 0:
        return {"value": None, "status": "insufficient_history"}

    slope = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in zip(x_values, y_values, strict=True)
    ) / variance
    prediction = y_mean + slope * (target_offset - x_mean)
    bounded_prediction = min(float(maximum), max(0.0, prediction))
    return {"value": int(round(bounded_prediction)), "status": "predicted"}
