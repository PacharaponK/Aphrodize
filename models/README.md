# Aphrodize model packages

This directory owns model source and model artifacts. `backend/` owns API requests, persistence, job orchestration, and model loading; it does not contain model implementations.

```text
models/
├── time-series/
│   └── non-linear-model/
└── non-time-series/
    ├── wrinkle-prototype/
    │   └── wrinkle_prototype.py
    └── u-net/
```

## Artifact policy

Do not commit datasets, checkpoints, model weights, generated masks, or experiment outputs here. Store those artifacts in MinIO through MLflow. Reserve `time-series/non-linear-model/` for reviewed non-linear forecasting models; do not place model source in a top-level `ai/` directory.

The hyphenated folder names match the platform taxonomy requested for this repository.
