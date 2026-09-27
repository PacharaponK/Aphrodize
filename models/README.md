# Aphrodize model packages

This directory owns model source and model artifacts. `backend/` owns API requests, persistence, job orchestration, and model loading; it does not contain model implementations.

```text
models/
├── time-series/
│   ├── linear-model/
│   │   └── lifestyle_aware_wrinkle_forecast.py
│   └── non-linear-model/
└── non-time-series/
    ├── wrinkle-prototype/
    │   └── wrinkle_prototype.py
    └── u-net/
```

## Artifact policy

Do not commit datasets, checkpoints, model weights, generated masks, or experiment outputs here. Store those artifacts in MinIO through MLflow. `time-series/linear-model/` contains transparent linear and Ridge models. Reserve `time-series/non-linear-model/` for reviewed non-linear forecasting models; do not place model source in a top-level `ai/` directory.

The hyphenated folder names match the platform taxonomy requested for this repository.
