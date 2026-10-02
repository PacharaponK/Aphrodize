# Daily lifestyle score model

This folder contains the inference code and source-controlled baseline artifact used by the Aphrodize daily-health API. The baseline Random Forest is a same-day tabular regressor, not a sequential model. Separately trained user-data candidates are one-day-ahead forecasters and are served only after explicit review and approval.

## Model contract

- Family: multi-output `RandomForestRegressor` (non-linear).
- Inputs: `sleep_duration_total_minutes`, full-day `water_intake_ml`, and `outdoor_exposure_choice` (choice code 1–4; not UV exposure).
- Outputs: synthetic `thirst_score_0_10` and `skin_dryness_score_0_10` on a 0–10 scale.
- Sleep score is calculated separately as `round(min(100, sleep_duration_total_minutes / 540 * 100), 1)`; inputs are accepted through 600 minutes (10 hours), while the score caps at 540 minutes (9 hours). This is an app-defined duration scale, not an ML output, age-adjusted medical score, or Zepp sleep-quality score.
- The production prediction endpoint abstains outside the estimator's training domain: sleep 180–540 minutes and water 900–1,800 ml. Thus 541–600 minute inputs are accepted and receive the duration score, but thirst/dryness predictions remain unavailable until the estimator is retrained and validated for that range. `POST /api/v1/daily-health/predict/test` remains a separate test-only path that can expose explicitly flagged experimental estimator output out of domain.
- Guidance is deterministic, individualized rule-based text using daily inputs and consented age, smoking, and menstrual context. It is not model output or a diagnosis; age-based sleep recommendations follow CDC public guidance.
- The API exposes input-domain status, feature-specific reasons, and prediction status; physically invalid inputs are rejected by request validation instead of being clipped into range.
- The API returns a three-tier daily attention summary (low, moderate, high) and a separate skin-care attention signal. These are experimental rule-based interpretations of synthetic scores and sleep duration, not probabilities, diagnoses, or model predictions.
- Optional age band (no birth date) requires a separate age-guidance consent from smoking/menstruation personalization consent. It adjusts only the general sleep-duration comparison because guidance differs by age; smoking and menstruation context never change the attention level. If no age band is chosen, sleep advice remains age-neutral.
- Next-day energy and thirst outputs remain insufficient_history until enough real user-reported outcomes are collected. Acne flare remains insufficient_data; no acne model is trained or claimed.
- User-reported next-day energy and thirst labels are stored separately from predictions for future evaluation; synthetic labels do not establish real-user or clinical accuracy.
- Approved user-trained candidates are loaded from `artifacts/user-candidates/<version-id>/` only when their registry status, feature/target contract, manifest, validation/test metrics, path, and model checksum all match. Inference responses identify the candidate and the one-day prediction horizon. If the active artifact fails any check, the API returns unavailable rather than silently switching to a different model.
- Operators can review versions at `GET /api/v1/daily-health/model-versions`, promote with `PUT /api/v1/daily-health/model-deployment` plus an approval reason, inspect the active pointer at `GET /api/v1/daily-health/model-deployment`, and restore the previous model with `POST /api/v1/daily-health/model-deployment/rollback`. These endpoints are protected by backend API credentials; no candidate is deployed automatically.
- Users can explicitly erase their account's daily entries, reported outcomes, profile context, consents, and user-trained candidate artifacts. Because candidate records do not keep per-user cohort membership, erasure conservatively invalidates every user-trained candidate and clears deployment, returning inference to the baseline. Imported CSV archive snapshots are not linked to account IDs; an operator must delete a whole snapshot by its SHA-256 fingerprint if needed.

## Artifact and provenance

Daily user-reported outcomes are accepted at PUT /api/v1/daily-health/users/{user_id}/outcomes and stored separately from predictions. Consent-gated profile context can be read or deleted at /api/v1/daily-health/users/{user_id}/profile.

`artifacts/daily_score_regression_v1/score_regressor.joblib` was trained on 1,083 synthetic rows from 20 synthetic users. It uses 300 trees and a 25%-user holdout split. `metrics.json` records the holdout metrics. Those metrics measure how well the model reproduces the synthetic label-generation rules; they do **not** establish clinical validity or real-user accuracy. Do not describe this artifact as medically validated. Replace or retrain it only after collecting consented, quality-checked user-reported target scores and evaluating on a separate user/time holdout.

Inference is loaded by `backend/libs/model_loader.py` and served at `POST /api/v1/daily-health/predict`; the `/predict/test` variant exists only for out-of-domain robustness experiments. The database stores predictions separately from user-reported outcomes; prediction values must never be reused as ground-truth labels. No accuracy claim is valid without matching real user-reported outcomes.

The estimator artifact was verified with scikit-learn 1.9.1 and joblib 1.6.0; the root project pins those versions because Python model serialization is version-sensitive. Retraining/replacing the artifact requires reviewing and updating the pins together.

The research trainer remains in `sandboxes/model/train_daily_score_regressors.py`; its default outputs remain sandbox-only. User-data candidates require a deliberate review of label provenance, validation and untouched test metrics, checksum, compatibility, and version ID. Metrics measure agreement with opted-in self-reports, not clinical accuracy.
