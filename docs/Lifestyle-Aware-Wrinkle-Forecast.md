# Lifestyle-Aware Wrinkle Forecast: Implementation Plan

## Current implementation

The backend persists a daily, pseudonymous record containing a standardized `wrinkle_score`, prior-night `sleep_hours`, daily `water_intake_ml`, and `outdoor_minutes`. A unique user/date constraint prevents duplicate daily records. The linear forecasting model lives at `models/time-series/linear-model/lifestyle_aware_wrinkle_forecast.py`; the API loads it from that taxonomy and the API Docker image explicitly includes `models/`.

`POST /api/v1/lifestyle-forecast/users/{user_id}/observations` adds a record. `GET /api/v1/lifestyle-forecast/users/{user_id}` returns `score_history` for the Day 1–30 actual-score graph, the model comparison, Day 25–30 rolling predictions for an actual-vs-predicted graph, and—only after 30 records—the selected-model Day 31–37 forecast.

## Forecast protocol

The baseline uses only the preceding score. The initial lifestyle model uses the preceding score, sleep, and outdoor values. A second Ridge candidate adds water only when its test MAE improves on the initial lifestyle model. Lagging every feature means a prediction for a date never reads values gathered on or after that date.

After the first 24 daily observations, each next day is predicted once with only the history already available. Test MAE is the selection criterion; RMSE is reported as a secondary error measure. The Ridge model standardizes numeric features and does not regularize its intercept.

For the seven-day recursive forecast, future lifestyle values are not known. The API explicitly holds the last recorded lifestyle values constant. This is an input assumption, never a behavioral recommendation.

## Collection checklist

1. Record sleep in the morning.
2. Record total water and outdoor minutes by the end of the day.
3. Calculate the score from three standardized, front-facing images.
4. Save one complete record for the day.

## Guardrails

- This one-person, 30-day proof of concept is not clinical research.
- Do not compare scores from different score-model versions or unstandardized image capture.
- The report exposes prediction associations only; it does not make causal or medical claims.
- The user can remove image-based analysis data through the existing deletion endpoint. Forecast observations are retained separately as self-reported history and should be covered by the product's consent and retention policy before production rollout.
