"""Short-horizon, leakage-safe linear wrinkle-score forecasting model.

The model belongs to the time-series model package. The backend owns storage,
validation, and transport; this module owns feature engineering, model fitting,
evaluation, and prediction. Results are predictive associations only, not
causal or clinical conclusions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import numpy as np

ModelKind = Literal["baseline", "lifestyle_core", "lifestyle_with_water"]

MINIMUM_OBSERVATIONS = 30
TRAINING_OBSERVATIONS = 24
TEST_OBSERVATIONS = 6
FEATURES: dict[ModelKind, tuple[str, ...]] = {
    "baseline": ("wrinkle_lag_1",),
    "lifestyle_core": ("wrinkle_lag_1", "sleep_hours_lag_1", "outdoor_minutes_lag_1"),
    "lifestyle_with_water": (
        "wrinkle_lag_1",
        "sleep_hours_lag_1",
        "water_intake_ml_lag_1",
        "outdoor_minutes_lag_1",
    ),
}
DISPLAY_NAMES: dict[ModelKind, str] = {
    "baseline": "Baseline",
    "lifestyle_core": "Lifestyle-aware",
    "lifestyle_with_water": "Lifestyle-aware + water",
}


@dataclass(frozen=True)
class DailyObservation:
    observed_on: date
    wrinkle_score: float
    sleep_hours: float
    water_intake_ml: float
    outdoor_minutes: float


@dataclass(frozen=True)
class Metrics:
    mae: float
    rmse: float


@dataclass(frozen=True)
class FittedModel:
    kind: ModelKind
    coefficients: np.ndarray
    feature_mean: np.ndarray
    feature_scale: np.ndarray

    def predict(self, values: Sequence[float]) -> float:
        normalized = (np.asarray(values, dtype=float) - self.feature_mean) / self.feature_scale
        return float(self.coefficients[0] + normalized @ self.coefficients[1:])


def feature_vector(observation: DailyObservation, kind: ModelKind) -> list[float]:
    values = {
        "wrinkle_lag_1": observation.wrinkle_score,
        "sleep_hours_lag_1": observation.sleep_hours,
        "water_intake_ml_lag_1": observation.water_intake_ml,
        "outdoor_minutes_lag_1": observation.outdoor_minutes,
    }
    return [values[name] for name in FEATURES[kind]]


def feature_pairs(
    observations: Sequence[DailyObservation], kind: ModelKind
) -> tuple[np.ndarray, np.ndarray]:
    """Create pairs from observations at t-1 to score targets at t."""
    feature_rows = [
        feature_vector(observations[index - 1], kind) for index in range(1, len(observations))
    ]
    targets = [observations[index].wrinkle_score for index in range(1, len(observations))]
    return np.asarray(feature_rows, dtype=float), np.asarray(targets, dtype=float)


def fit_model(observations: Sequence[DailyObservation], kind: ModelKind) -> FittedModel:
    if len(observations) < 2:
        raise ValueError("At least two daily observations are required to fit a forecast model.")
    features, target = feature_pairs(observations, kind)
    mean = features.mean(axis=0)
    scale = features.std(axis=0)
    scale[scale == 0] = 1.0
    normalized = (features - mean) / scale
    design = np.column_stack([np.ones(len(normalized)), normalized])

    if kind == "baseline":
        coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
    else:
        # Ridge penalty excludes the intercept, after every numeric feature is standardized.
        penalty = np.eye(design.shape[1])
        penalty[0, 0] = 0.0
        coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ target)
    return FittedModel(kind, coefficients, mean, scale)


def rolling_predictions(
    observations: Sequence[DailyObservation], kind: ModelKind
) -> tuple[list[float], list[float]]:
    actual: list[float] = []
    predicted: list[float] = []
    for target_index in range(TRAINING_OBSERVATIONS, TRAINING_OBSERVATIONS + TEST_OBSERVATIONS):
        model = fit_model(observations[:target_index], kind)
        predicted.append(model.predict(feature_vector(observations[target_index - 1], kind)))
        actual.append(observations[target_index].wrinkle_score)
    return actual, predicted


def metrics(actual: Sequence[float], predicted: Sequence[float]) -> Metrics:
    error = np.asarray(actual) - np.asarray(predicted)
    return Metrics(
        mae=round(float(np.abs(error).mean()), 3),
        rmse=round(float(np.sqrt(np.mean(error**2))), 3),
    )


def _is_daily(observations: Sequence[DailyObservation]) -> bool:
    return all(
        (observations[index].observed_on - observations[index - 1].observed_on).days == 1
        for index in range(1, len(observations))
    )


def build_report(observations: Sequence[DailyObservation], forecast_days: int = 7) -> dict:
    """Build chart-ready history, rolling evaluation, and a selected-model forecast."""
    if forecast_days < 1 or forecast_days > 7:
        raise ValueError("forecast_days must be between 1 and 7.")
    ordered = sorted(observations, key=lambda item: item.observed_on)
    if len({item.observed_on for item in ordered}) != len(ordered):
        raise ValueError("Only one observation per calendar date is allowed.")

    daily = _is_daily(ordered)
    ready = len(ordered) >= MINIMUM_OBSERVATIONS and daily
    report: dict = {
        "observation_count": len(ordered),
        "required_observations": MINIMUM_OBSERVATIONS,
        "ready_for_evaluation": ready,
        "score_history": [
            {"date": item.observed_on.isoformat(), "wrinkle_score": item.wrinkle_score}
            for item in ordered
        ],
        "models": [],
        "selected_model": None,
        "test_predictions": [],
        "forecast": [],
        "limitations": [
            "This is a short-term association-for-prediction tool, not clinical advice "
            "or causal evidence.",
            "Lighting, pose, expression, and image quality can change a wrinkle score.",
        ],
    }
    if not daily:
        report["message"] = (
            "Daily observations contain a date gap. A continuous 30-day collection period is "
            "required before evaluating or forecasting."
        )
        return report
    if len(ordered) < MINIMUM_OBSERVATIONS:
        report["message"] = (
            f"Record {MINIMUM_OBSERVATIONS - len(ordered)} more daily observations before the "
            "Day 25-30 rolling evaluation and Day 31-37 forecast are available."
        )
        return report

    comparison: dict[ModelKind, tuple[Metrics, list[float], list[float]]] = {}
    for kind in FEATURES:
        actual, predicted = rolling_predictions(ordered, kind)
        result_metrics = metrics(actual, predicted)
        comparison[kind] = result_metrics, actual, predicted
        report["models"].append(
            {
                "name": kind,
                "display_name": DISPLAY_NAMES[kind],
                "features": list(FEATURES[kind]),
                "test_mae": result_metrics.mae,
                "test_rmse": result_metrics.rmse,
            }
        )

    core_mae = comparison["lifestyle_core"][0].mae
    water_mae = comparison["lifestyle_with_water"][0].mae
    lifestyle_choice: ModelKind = (
        "lifestyle_with_water" if water_mae < core_mae else "lifestyle_core"
    )
    selected: ModelKind = (
        lifestyle_choice
        if comparison[lifestyle_choice][0].mae < comparison["baseline"][0].mae
        else "baseline"
    )
    report["selected_model"] = {
        "name": selected,
        "display_name": DISPLAY_NAMES[selected],
        "selection_rule": (
            "lowest test MAE; water is retained only when it improves the core lifestyle MAE"
        ),
    }
    report["test_predictions"] = [
        {
            "date": ordered[index].observed_on.isoformat(),
            "actual": ordered[index].wrinkle_score,
            "baseline_predicted": round(
                comparison["baseline"][2][index - TRAINING_OBSERVATIONS], 3
            ),
            "lifestyle_predicted": round(
                comparison[lifestyle_choice][2][index - TRAINING_OBSERVATIONS], 3
            ),
            "lifestyle_model": lifestyle_choice,
        }
        for index in range(TRAINING_OBSERVATIONS, TRAINING_OBSERVATIONS + TEST_OBSERVATIONS)
    ]

    model = fit_model(ordered, selected)
    latest = ordered[-1]
    score = latest.wrinkle_score
    report["forecast_assumption"] = (
        "Future sleep, water intake, and outdoor time are held at the most recently recorded "
        "values."
    )
    for offset in range(1, forecast_days + 1):
        assumed_day = DailyObservation(
            observed_on=latest.observed_on,
            wrinkle_score=score,
            sleep_hours=latest.sleep_hours,
            water_intake_ml=latest.water_intake_ml,
            outdoor_minutes=latest.outdoor_minutes,
        )
        score = max(0.0, min(100.0, model.predict(feature_vector(assumed_day, selected))))
        report["forecast"].append(
            {
                "date": (latest.observed_on + timedelta(days=offset)).isoformat(),
                "predicted_wrinkle_score": round(score, 3),
            }
        )
    return report
