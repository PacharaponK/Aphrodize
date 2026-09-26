from datetime import date, timedelta

from backend.libs.model_loader import get_lifestyle_forecast_model

forecast_model = get_lifestyle_forecast_model()
DailyObservation = forecast_model.DailyObservation
build_report = forecast_model.build_report


def observations(count: int) -> list[DailyObservation]:
    first_day = date(2026, 9, 1)
    return [
        DailyObservation(
            observed_on=first_day + timedelta(days=index),
            wrinkle_score=45 + index * 0.2,
            sleep_hours=6 + (index % 3),
            water_intake_ml=1800 + index * 10,
            outdoor_minutes=30 + (index % 5) * 10,
        )
        for index in range(count)
    ]


def test_report_waits_for_the_full_collection_period() -> None:
    report = build_report(observations(24))
    assert report["ready_for_evaluation"] is False
    assert report["models"] == []
    assert report["forecast"] == []


def test_report_compares_models_and_forecasts_after_30_days() -> None:
    report = build_report(observations(30))
    assert report["ready_for_evaluation"] is True
    assert len(report["models"]) == 3
    assert len(report["score_history"]) == 30
    assert len(report["test_predictions"]) == 6
    assert len(report["forecast"]) == 7
    assert report["forecast"][0]["date"] == "2026-10-01"
    assert report["selected_model"]["name"] in {
        "baseline",
        "lifestyle_core",
        "lifestyle_with_water",
    }


def test_report_rejects_a_collection_with_daily_gaps() -> None:
    records = [
        DailyObservation(
            observed_on=item.observed_on + timedelta(days=1 if index >= 15 else 0),
            wrinkle_score=item.wrinkle_score,
            sleep_hours=item.sleep_hours,
            water_intake_ml=item.water_intake_ml,
            outdoor_minutes=item.outdoor_minutes,
        )
        for index, item in enumerate(observations(30))
    ]
    report = build_report(records)
    assert report["ready_for_evaluation"] is False
    assert report["forecast"] == []
