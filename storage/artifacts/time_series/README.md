# Time-series research artifacts

Use this directory for reviewed longitudinal trend, feature, and forecast reports. It is a research output workspace; the running API does not scan it automatically.

Active UV forecasts and lifecycle reports are written to `storage/artifacts/uv/`, with versioned model bundles under `storage/models/uv/`. Follow the [UV workflow](../../../docs/uv-model-workflow.md) instead of copying a report here to deploy a model. Daily Health candidate artifacts have their own [model contract](../../../models/time-series/non-linear-model/README.md).

Historical local longitudinal observations may use `storage/data/time_serie/longitudinal/`; current account health records live in PostgreSQL. Neither private observations nor generated prediction records belong in Git. Consent and user-reported outcomes are prerequisites for user-data training; predictions are not labels.

This folder is not wholly ignored. Check new outputs with `git status --short -- storage/artifacts/time_series` from the repository root. Keep only intentionally reviewed, non-sensitive reports in version control; see [storage policy](../../README.md).
