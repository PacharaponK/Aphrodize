# Operational scripts

Run commands from the repository root. PowerShell scripts need PowerShell and Docker Compose; Python scripts need the locked backend dependencies unless their guide specifies a separate runtime. These commands can create files, contact data sources, or modify deployment state; inspect the relevant guide before running operator actions.

## Health and logs

```powershell
# Base services, or the full local AI profile.
.\scripts\check-health.ps1
.\scripts\check-health.ps1 -Profiles ai

# Snapshot latest 500 lines per service; follow instead of writing a snapshot.
.\scripts\export-logs.ps1 -Tail 500
.\scripts\export-logs.ps1 -Follow
```

`check-health.ps1` checks the selected configuration's containers/health, one-shot completion, and authenticated API readiness. Pass the profiles you actually started. For another Compose configuration, use `-ComposeFiles`, for example `-ComposeFiles compose.vm.yml`; that file also needs its deployment environment. A nonzero exit indicates a failed check, not necessarily a dead API process.

Log exports use the default Compose selection, write under root `logs/`, and may contain sensitive operational data. See the [log guide](../logs/README.md).

## UV operations

| Script | Purpose |
| --- | --- |
| `prepare_uv_dataset.py` | Download/normalize public TEMIS observations into `storage/data/uv/` |
| `train_uv_model.py` | Train versioned city SARIMAX candidates; does not select serving deployment |
| `evaluate_uv_model.py` | Evaluate a model bundle and recorded backtests |
| `uv_mlops.py` | Bootstrap, train/gate candidates, inspect state, explicitly promote/rollback |
| `refresh_uv_forecast.py` | Refresh snapshots using approved active models and public data |
| `prepare_uv_map.py` | Generate static province map assets from reviewed boundary inputs |
| `seed_uv_products.py` | Seed reviewed UV product records using the configured database |

Inspect lifecycle commands without changing deployment:

```powershell
uv run --no-sync python scripts/uv_mlops.py --help
uv run --no-sync python scripts/uv_mlops.py status
```

A fresh clone has no active UV bundle. Follow [model workflow](../docs/uv-model-workflow.md), [UV MLOps](../docs/uv-mlops-report.md), and [map setup](../docs/uv-thailand-map.md) for ordering, data/rights requirements, and approval. `background` refresh and `uv-training` profiles are optional; training is not automatic promotion.

## Deployment and monitoring

Release/deployment tools include `release_manifest.py`, `deploy_vm.py`, `deploy-vm.sh`, and `check-vm-readiness.py`. Use the [VM deployment](../docs/deploy-vm.md) and [CI/CD guide](../docs/cicd-vm.md) for required inputs; do not run deployment commands as generic health checks.

Observability tools include `configure_observability.py`, readiness checks, dashboard generation, and `external_probe.py`. Follow [observability setup](../docs/observability.md); an independent external probe belongs on another host. Keep rendered configuration and credentials private.

AI-specific prediction/evaluation CLIs live in `ai/scripts/`; database/bucket/fixture utilities live in `backend/scripts/`. See [AI](../ai/README.md) and [backend](../backend/README.md). `check_wrinkle_training.py` and `smoke_ai_ecosystem.py` are specialized checks with their own prerequisites, not fresh-clone quick starts.
