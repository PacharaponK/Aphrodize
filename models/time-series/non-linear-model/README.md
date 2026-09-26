# Daily lifestyle score model

This folder contains the estimator artifact and inference code used by the Aphrodize daily-health API. It is placed under the requested time-series taxonomy, but the current Random Forest is a **same-day tabular regressor**, not a sequential model and not a next-day forecaster.

## Model contract

- Family: multi-output `RandomForestRegressor` (non-linear).
- Inputs: `sleep_duration_total_minutes`, full-day `water_intake_ml`, and `outdoor_exposure_choice` (choice code 1–4; not UV exposure).
- Outputs: synthetic `thirst_score_0_10` and `skin_dryness_score_0_10` on a 0–10 scale.
- Sleep score is calculated separately as `min(100, sleep_duration_total_minutes / 420 * 100)`; it is not an ML output or a Zepp sleep-quality score.
- Score inference abstains outside the training domain: sleep 180–540 minutes and water 900–1,800 ml.
- Guidance is deterministic rule-based text, not model output or medical advice.

## Artifact and provenance

`artifacts/daily_score_regression_v1/score_regressor.joblib` was trained on 1,083 synthetic rows from 20 synthetic users. It uses 300 trees and a 25%-user holdout split. `metrics.json` records the holdout metrics. Those metrics measure how well the model reproduces the synthetic label-generation rules; they do **not** establish clinical validity or real-user accuracy. Do not describe this artifact as medically validated. Replace or retrain it only after collecting consented, quality-checked user-reported target scores and evaluating on a separate user/time holdout.

Inference is loaded by `backend/libs/model_loader.py` and served at `POST /api/v1/daily-health/predict`. The database stores predictions separately from user-reported outcomes; prediction values must never be reused as ground-truth labels.

The estimator artifact was verified with scikit-learn 1.9.1 and joblib 1.6.0; the root project pins those versions because Python model serialization is version-sensitive. Retraining/replacing the artifact requires reviewing and updating the pins together.

The research trainer remains in `sandboxes/model/train_daily_score_regressors.py`; its default outputs remain sandbox-only. Promoting a new artifact requires a deliberate review of its target labels, evaluation report, compatibility, and model ID.
