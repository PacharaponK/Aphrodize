# Aphrodize model workspaces

Model source is split by purpose. Backend services load models and manage requests, persistence, consent, queues, and deployment state. Active FFHQ-Wrinkle implementation lives in `ai/`; this directory also contains a Daily Health baseline and research notebooks.

| Path | Status / use |
| --- | --- |
| `time-series/non-linear-model/` | Daily Health inference source and explicitly committed synthetic baseline; [contract and use](time-series/non-linear-model/README.md) |
| `time-series/uv/uv_model_evaluation.ipynb` | UV evaluation notebook; training/refresh entry points live in root `scripts/` |
| `time-series/linear-model/` | Reserved workspace; no deployed implementation |
| `non-time-series/u-net/` | Reserved research workspace; active wrinkle inference is in [AI](../ai/README.md) |
| `non-time-series/wrinkle-prototype/` | Legacy prototype and evaluation notebook; not the deployed FFHQ pipeline |

Hyphenated directory names are workspace labels, not Python import paths. The Daily Health baseline is a same-day tabular regressor despite its historical time-series location. The UV city model is a SARIMAX forecaster; see [UV workflow](../docs/uv-model-workflow.md).

## Use the deployed paths

Start the [backend stack](../README.md) and use the documented APIs. Do not execute legacy prototype code to reproduce current application results. For local image inference use `python ai/scripts/predict_wrinkle.py --help` in the separate [AI environment](../ai/README.md). For Daily Health use `/api/v1/daily-health/predict`; see the [baseline guide](time-series/non-linear-model/README.md).

## Artifact policy

Keep new datasets, checkpoints, masks, user records, and generated experiment outputs outside Git. FFHQ runtime files belong in `storage/models/ffhq-wrinkle/`; UV bundles belong in `storage/models/uv/`. Controlled training records experiments through MLflow/MinIO where configured.

The existing `daily_score_regression_v1/score_regressor.joblib` and `metrics.json` are an explicit source-controlled baseline exception. Keep scikit-learn/joblib pins compatible with that trusted artifact. Never load untrusted pickle/joblib files. Training creates candidates; approval and deployment are separate operations. See [storage](../storage/README.md) and [training documentation](../docs/README.md).
