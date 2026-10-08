# Daily Health score model

This directory contains inference helpers and the committed synthetic baseline used by the Daily Health API. Its historical time-series folder name does not make the baseline a sequential model: it is a same-day multi-output Random Forest. Separately trained, approved user-data candidates can have a one-day prediction horizon.

## Run and verify

Start the backend using the [root guide](../../../README.md). Use the web dashboard for normal input, or open <http://localhost:8000/docs> and call `POST /api/v1/daily-health/predict` with service Basic credentials. Example JSON:

```json
{
  "local_date": "2026-10-08",
  "sleep_hours": 7,
  "sleep_minutes": 30,
  "water_intake_ml": 1500,
  "weight_kg": 60,
  "outdoor_exposure_choice": 2
}
```

Use the date of the observation. `weight_kg` is optional; without it the fluid-shortfall score is unavailable. Personal age, smoking, menstrual, and skin-type context has separate consent requirements in the request schema. Previewing a prediction does not save an account record.

With the locked backend development environment installed, run from the repository root:

```powershell
uv run --no-sync python -m pytest tests/test_daily_score_model.py tests/test_daily_health.py tests/test_model_review_authorization.py
```

The backend loads this module through [model_loader.py](../../../backend/libs/model_loader.py); the hyphenated folder is not a normal Python package import path.

## Current output contract

| Output | Source / limit |
| --- | --- |
| Sleep duration score | `round(min(100, total_sleep_minutes / 540 * 100), 1)`; accepts up to 600 minutes but caps at nine hours |
| `thirst_score_0_10` | Calculated recorded-fluid shortfall: `round(10 * max(0, 1 - water_intake_ml / (weight_kg * 30)), 1)`; unavailable without weight or for the unsupported adolescent age band |
| `skin_dryness_score_0_10` | Experimental estimator output; synthetic baseline does not establish real-user accuracy |
| Attention/guidance | Deterministic rules and consented context, not model probabilities or diagnoses |
| Next-day forecasts | Require sufficient real user-reported history and eligible reviewed models; otherwise remain unavailable |

The fluid score is not measured thirst or dehydration. Sleep score is an app-defined duration scale, not sleep quality or an age-adjusted medical score. Smoking/menstrual context does not change the attention level. Acne forecasting remains insufficient-data; no acne model is claimed.

Estimator inputs are sleep duration, full-day water intake, and outdoor-exposure choice code 1–4 (not UV exposure). Baseline training-domain bounds are sleep **180–540 minutes** and water **900–1,800 ml**. Valid requests outside that domain still receive eligible calculations but withhold estimator dryness output. `/predict/test` can expose explicitly flagged experimental out-of-domain output; it is for robustness evaluation, not normal product guidance. Invalid physical inputs are rejected rather than clipped into range.

## Baseline provenance

`artifacts/daily_score_regression_v1/score_regressor.joblib` was trained on 1,083 synthetic rows from 20 synthetic users, using 300 trees and a 25%-user holdout. [metrics.json](artifacts/daily_score_regression_v1/metrics.json) measures reproduction of synthetic label-generation rules. The serialized model has two historical targets; the current API computes the displayed fluid-shortfall score separately.

The root project pins scikit-learn **1.9.1** and joblib **1.6.0** for artifact compatibility. Review those pins together with any baseline replacement. Load only trusted serialized artifacts. The research trainer is under local `sandboxes/` and is not part of a fresh clone.

## User-data candidates and approval

User-reported outcomes are stored separately from predictions. Predictions must never become ground-truth training labels. See the [training pipeline](../../../docs/lifestyle/Daily-Health-Training-Pipeline.md) for consent, import, training, and evidence requirements.

Approved candidates under `artifacts/user-candidates/<version-id>/` require matching registry status, feature/target contract, manifest, validation/test metrics, path, and checksum. An invalid active artifact returns unavailable instead of silently switching models.

Model review endpoints use **separate admin Basic credentials**, distinct from service API credentials:

- `GET /api/v1/daily-health/model-versions`: inspect candidates.
- `GET` / `PUT /api/v1/daily-health/model-deployment`: inspect or promote with an approval reason.
- `POST /api/v1/daily-health/model-deployment/rollback`: restore the previous deployment.

No candidate deploys automatically. Users can erase account health records, context, consents, and user-trained candidate artifacts. Because cohort membership is not tracked per candidate, erasure conservatively invalidates all user-trained candidates and clears deployment. Imported archive snapshots are not linked to account IDs; operators must delete the relevant whole snapshot by SHA-256 when needed.
