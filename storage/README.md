# Aphrodize storage

Local datasets, model files, and generated results belong here. Application uploads and queued workflow artifacts use private MinIO buckets; this filesystem tree is not a public upload directory.

## Current paths

| Path | Contents / producer |
| --- | --- |
| `data/ffhq-wrinkle/` | Optional licensed FFHQ research images, masks, and test lists |
| `models/ffhq-wrinkle/` | Runtime U-Net, BiSeNet, YuNet, optional SwinUNETR; [setup](../ai/README.md) |
| `data/approved/` | Reviewed curated training datasets/manifests; [training guide](../docs/ai/Curated-Training.md) |
| `data/uv/` | Downloaded/normalized UV observations |
| `models/uv/versions/` | Immutable trained UV bundles; `models/uv/active.json` selects deployment |
| `artifacts/uv/` | Generated forecast/map snapshots and lifecycle reports |
| `artifacts/ffhq_wrinkle_phase*/` | Phase-specific research outputs |
| `artifacts/non_time_series/` | Committed EDA references and local non-sequential reports; [guide](artifacts/non_time_series/README.md) |
| `artifacts/time_series/` | Longitudinal/trend research reports; [guide](artifacts/time_series/README.md) |
| `logs/` | Local application/worker logs; Compose exports instead use root `logs/` |

FFHQ canonical paths are in [paths.py](../ai/ffhq_wrinkle/paths.py). Historical `data/non_time_serie/` and `data/time_serie/` paths are legacy research locations, not active API storage. Match directory spelling to the code that produces/reads each artifact.

## Prepare only what you use

For image inference, follow the [AI guide](../ai/README.md); no FFHQ dataset is needed. For UV, follow the [UV model workflow](../docs/uv-model-workflow.md) and [map setup](../docs/uv-thailand-map.md). Missing or stale snapshots can produce unavailable API responses. Empty directories created by bind mounts do not mean artifacts are ready.

Docker paths differ from host paths: for example, host `storage/models/ffhq-wrinkle/` is mounted as `/app/storage/models/ffhq-wrinkle/` in workers. API and inference mounts can be read-only; candidate training needs its documented writable mounts. Use container paths for environment variables passed to containers.

## Git and retention

`data/`, runtime weights, UV outputs, and selected generated paths are ignored. Some EDA reports/images are deliberately tracked; **not every new file under `artifacts/` is ignored**. Check a destination before generating large or sensitive outputs:

```powershell
# From the repository root; a matching rule means this path is ignored.
git check-ignore -v storage/models/ffhq-wrinkle/stage2_wrinkle_finetune_unet/stage2_unet.pth
git status --short --untracked-files=normal -- storage
```

Do not force-add private images, health records, checkpoints, logs, or credentials. Put human-readable implementation reports in `docs/ai/implementation/`. The committed Daily Health baseline under `models/` is a deliberate exception described in the [model policy](../models/README.md).

Deleting local files can break inference, evaluation, or deployment references. Back up approved bundles and required data before cleanup. Docker named volumes are separate; deleting this tree does not erase database/MinIO volumes, and `docker compose down -v` does not remove host bind-mounted files.
