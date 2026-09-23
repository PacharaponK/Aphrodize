# Storage

This storage tree belongs to Aphrodize only. Source data is kept separate from
generated artifacts so that large or sensitive files are never committed.

```text
storage/
├── data/
│   ├── ffhq-wrinkle/                  # FFHQ images, labels and masks
│   ├── non_time_serie/ffhq_wrinkle/  # legacy prototype data
│   └── time_serie/longitudinal/      # consented timestamped observations
├── models/
│   └── ffhq-wrinkle/                  # U-Net, SwinUNETR, BiSeNet and YuNet
├── artifacts/
│   ├── non_time_serie/               # EDA, model metrics, visualizations
│   └── time_serie/                   # trend and forecast outputs
└── logs/                              # local application/worker logs
```

Phase artifacts, raw images, masks, model weights, user data and logs are local
and ignored by Git. Commit human-readable implementation reports under
`docs/implementation/` instead.

The canonical paths used by Python code are defined in
`ai/ffhq_wrinkle/paths.py`; avoid adding dataset or model paths directly inside
source modules.
