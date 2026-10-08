# Aphrodize

A privacy-first skin-tracking and ML workflow application: Next.js, FastAPI, PostgreSQL, Redis/ARQ workers, private MinIO storage, Label Studio, and MLflow. Model outputs are experimental and are not diagnoses or treatment predictions.

## Workspace guides

| Section | Guide |
| --- | --- |
| Web client, sessions, capture, recommendations, admin UI | [frontend](frontend/README.md) |
| API, authentication, queues, database, fixtures | [backend](backend/README.md) |
| Wrinkle models, CLI, research API, evaluation | [AI](ai/README.md) |
| Daily Health baseline and model workspaces | [models](models/README.md) |
| Datasets, weights, generated outputs | [storage](storage/README.md) |
| Operational commands | [scripts](scripts/README.md) |
| Container images and deployment configurations | [Docker](docker/README.md) |
| Log exports | [logs](logs/README.md) |
| Architecture, consent, training, deployment, monitoring | [documentation index](docs/README.md) |

## Requirements

- Docker Desktop with Linux containers and Docker Compose v2. Builds download images, packages, and a MediaPipe asset; allow network access and sufficient disk space.
- PowerShell for the examples below. Run commands from the repository root unless a step says otherwise.
- Node.js 24 and pnpm 11.19.0 for the web client, which runs separately from the default Compose stack.
- Python 3.11 and `uv` for backend development/tests outside Docker. The optional AI research environment uses Python 3.9 via Conda and stays separate.

## 1. Configure the local stack

Create `.env` only if it does not already exist:

```powershell
Copy-Item .env.example .env
```

Edit `.env` before startup. Replace `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_SECRET_KEY` (at least eight characters), `LABEL_STUDIO_PASSWORD`, `API_PASSWORD`, and `JWT_SECRET_KEY` with your own secrets. Keep them out of Git. In the base development Compose file, PostgreSQL is initialized as user/database `aphrodize`; keep those defaults. Changing `.env` passwords does not reset credentials inside existing database volumes.

For administration, also set `ADMIN_USERNAME` and an `ADMIN_PASSWORD` of at least eight characters. Use credentials distinct from `API_USERNAME`/`API_PASSWORD` for model review.

## 2. Start backend services

For accounts and Daily Health without image processing:

```powershell
docker compose up -d --build
docker compose ps --all
curl.exe --fail http://localhost:8000/api/v1/health
```

For capture, annotation, and training, prepare the runtime weights in [AI setup](ai/README.md), then enable the AI services:

```powershell
docker compose --profile ai up -d --build
docker compose --profile ai ps --all
.\scripts\check-health.ps1 -Profiles ai
```

`minio-init` should exit with code `0`; it creates the private, annotation, and MLflow buckets. Other enabled services should remain running. Container health does not prove that weights or a confidence release are ready. `/api/v1/health` reports API liveness; the health script also checks authenticated readiness, which can fail when required dependencies are unavailable.

| Service | Local URL | Enabled by |
| --- | --- | --- |
| API docs | <http://localhost:8000/docs> | Base stack |
| API liveness | <http://localhost:8000/api/v1/health> | Base stack |
| MinIO API / console | <http://localhost:9000> / <http://localhost:9001> | `ai` profile |
| Label Studio | <http://localhost:8080> | `ai` profile |
| MLflow | <http://localhost:5000> | `ai` profile |
| PostgreSQL / Redis / workers | Internal Compose network | Base / `ai` profile |

Use `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` for MinIO and `LABEL_STUDIO_USERNAME`/`LABEL_STUDIO_PASSWORD` for Label Studio. API operations use service Basic credentials, user Bearer tokens, or separate admin Basic credentials; check each operation in OpenAPI.

## 3. Start the web client

Follow [frontend configuration](frontend/README.md) to create `frontend/.env.local` with backend credentials and a random session secret before using capture or account flows. Then:

```powershell
Set-Location frontend
npm install --global pnpm@11.19.0 --ignore-scripts
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://localhost:3000>. Accounts, Daily Health, capture/results, and recommendations connect to backend services. Image capture needs the AI profile and verified weights; UV pages need current forecast/map snapshots. Return to the repository root before subsequent Docker commands.

## 4. Optional demo account and catalog

With the backend running:

```powershell
docker compose --profile demo run --rm fixture
```

Sign in at <http://localhost:3000/login> with `demo@example.local` / `demo-password-123`. The [fixture](backend/fixtures/users.yaml) preserves existing accounts and avoids duplicate entries. Fixture health records are excluded from user-model training. Use this account only for local development.

Load reviewed products separately:

```powershell
docker compose exec -T api python -m backend.scripts.load_fixtures --products /app/backend/fixtures/products.yaml

# Optional additional reviewed wrinkle-care products.
docker compose exec -T api python -m backend.scripts.load_fixtures --products /app/backend/fixtures/wrinkle-products-2026-10-07.yaml
```

These imports add products without users or profiles and preserve admin edits and archived products. Recommendations may withhold named products because of consent, release status, allergy history, or missing verified shopping metadata. Prices in the [base catalog research](docs/research/thai-product-catalog-2026-10-01.md) and [additional wrinkle-care review](docs/research/wrinkle-product-catalog-2026-10-07.md) are dated snapshots.

## Model readiness

- **Wrinkles:** weights are absent from Git. The default confidence policy withholds scores/recommendations. Select a matching reviewed policy or passed calibration bundle deliberately; see [AI setup](ai/README.md).
- **Daily Health:** the committed baseline reproduces synthetic labels; its metrics do not establish real-user accuracy. Sleep and fluid-shortfall scores are calculations. User-data candidates need separate consent, evaluation, and admin approval; see the [model contract](models/time-series/non-linear-model/README.md).
- **UV:** clone alone provides neither current snapshots nor approved models. Follow the [UV workflow](docs/uv-model-workflow.md) and [UV MLOps guide](docs/uv-mlops-report.md) before enabling `background` or `uv-training`.
- **Generic jobs:** submitting time-series/tabular inference does not deploy an estimator; unsupported deployments fail with `model_not_deployed`.

For human annotation, use the [Label Studio guide](docs/ai/Annotation-Review.md). For curated datasets and candidate deployment, use the [controlled training guide](docs/ai/Curated-Training.md). Training does not automatically publish a candidate.

## Development checks

From the repository root, use the locked Python 3.11 environment used by CI:

```powershell
uv sync --python 3.11 --locked --no-default-groups --group ci --no-install-package opencv-python
uv run --no-sync python -m pytest
uv run --no-sync ruff check backend tests
```

See the [frontend](frontend/README.md) and [AI](ai/README.md) guides for their checks. Do not combine the research PyTorch/NumPy environment with the backend environment.

## Operations and troubleshooting

```powershell
# Inspect startup failures.
docker compose --profile ai logs --tail 100 api inference-worker trainer-worker

# Export a local snapshot or follow logs.
.\scripts\export-logs.ps1
.\scripts\export-logs.ps1 -Follow

# Apply environment changes and rebuild local services.
docker compose --profile ai up -d --build

# Stop enabled services while retaining data volumes.
docker compose --profile ai down
```

The API reloads mounted backend code in development; workers need a restart after source changes. Use `up -d` to apply changed environment variables. If capture stays queued, check the inference worker, Redis, MinIO, and weights. For `401`, check the credential type and matching frontend/backend settings; admin `503` can indicate missing or insufficient admin configuration. Resolve port conflicts or update both Compose and client URLs.

`docker compose --profile ai down -v` also deletes persisted database, queue, object-store, and annotation volumes. Use it only when intentionally discarding local data.

The base stack is for development. Use the [VM](docs/deploy-vm.md), [GPU](docs/deploy-gpu.md), and [observability](docs/observability.md) guides for deployment. Monitoring is opt-in. Keep photos, health records, secrets, logs, and generated checkpoints private; analysis, annotation, and training consent are separate decisions.
