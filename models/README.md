# Aphrodize model packages

This directory is the reserved model workspace. It is deliberately separated from `backend/`, which owns API requests, persistence, and ARQ jobs.

```text
models/
├── time-series/
│   └── modelx/
└── non-time-series/
    └── u-net/
```

## Artifact policy

Do not commit datasets, checkpoints, model weights, generated masks, or experiment outputs here. Store those artifacts in MinIO through MLflow. The folders contain no Python implementation yet; they reserve the intended model locations only.

The hyphenated folder names match the platform taxonomy requested for this repository.
