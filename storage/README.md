# Storage

This storage tree belongs to Aphrodize only. Source data is kept separate from
generated artifacts so that large or sensitive files are never committed.

```text
storage/
├── data/
│   ├── non_time_serie/ffhq_wrinkle/  # FFHQ images and wrinkle masks
│   └── time_serie/longitudinal/      # consented timestamped observations
├── artifacts/
│   ├── non_time_serie/               # EDA, model metrics, visualizations
│   └── time_serie/                   # trend and forecast outputs
└── logs/                              # local application/worker logs
```

Commit small reports and reproducible visualizations under `artifacts/`; do not
commit raw images, masks, model weights, user data, or logs.
