# Aphrodize

**A local MLOps platform for time-series and non-time-series model workflows.**

Aphrodize is a Docker Compose–based modular monolith for managing private data, annotation, asynchronous inference and training jobs, and experiment tracking. It provides the platform foundation; production model packages, datasets, checkpoints, and trained weights are intentionally out of scope for this repository.

> Current status: image analyses run the checked FFHQ-Wrinkle model through the inference worker. Generic time-series and tabular inference still fails safely with `model_not_deployed` until an approved MLflow model is integrated.

## Included services

| Service | Local address | Purpose |
|---|---|---|
| FastAPI | [http://localhost:8000/docs](http://localhost:8000/docs) | Versioned REST API and OpenAPI documentation |
| PostgreSQL | Internal Compose network | Workflow metadata and application records through async SQLAlchemy |
| Redis | Internal Compose network | Authenticated ARQ job queues |
| MinIO API | [http://localhost:9000](http://localhost:9000) | Private application and MLflow object storage |
| MinIO Console | [http://localhost:9001](http://localhost:9001) | Local object-storage administration |
| Label Studio | [http://localhost:8080](http://localhost:8080) | Human-operated annotation UI; local registration is enabled |
| MLflow | [http://localhost:5000](http://localhost:5000) | Training-run and artifact tracking |
| Inference worker | Internal Compose network | ARQ worker for inference jobs |
| Trainer worker | Internal Compose network | ARQ worker for model-training jobs |

The platform uses separate Redis queues for training and inference. MinIO buckets are initialized automatically when the stack starts.

## Architecture

```text
Client
  -> FastAPI API
     -> PostgreSQL: consent, questionnaire, job metadata, results
     -> MinIO: private source data, derived artifacts, MLflow artifacts
     -> Redis / ARQ
          -> inference worker
          -> trainer worker -> MLflow
     -> Label Studio SDK -> Label Studio
```

For design decisions and data-flow detail, see [docs/architecture.md](docs/architecture.md).

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose v2 enabled
- PowerShell 5.1+ or PowerShell 7+ on Windows
- Git, if cloning the repository

You do not need Python installed to run the complete local Docker stack. Python 3.11+ is only required for local linting or tests outside Docker.

## Run locally

### 1. Create local configuration

Copy the example configuration. The `.env` file is ignored by Git, so credentials stay local.

```powershell
Copy-Item .env.example .env
```

Open `.env` and set strong local values for these required secrets before starting:

```dotenv
POSTGRES_PASSWORD=replace-me
REDIS_PASSWORD=replace-me
MINIO_SECRET_KEY=replace-me
LABEL_STUDIO_PASSWORD=replace-me
API_PASSWORD=replace-me
```

You may also change the matching usernames, plus `MINIO_ACCESS_KEY`, `LABEL_STUDIO_USERNAME`, and `API_USERNAME`. Keep the values in `.env`; do not commit this file.

The image worker expects the FFHQ-Wrinkle runtime files under `storage/models/ffhq-wrinkle/`; see [ai/README.md](ai/README.md) for the required layout and checksums. Compose mounts this directory read-only.

### 2. Build and start services

```powershell
docker compose up -d --build
```

Check the startup state:

```powershell
docker compose ps
```

`minio-init` is expected to finish with exit code `0`; it creates the `aphrodize-private` and `mlflow` buckets. The remaining services should continue running.

### 3. Verify the stack

Run the repository health checker after the containers have started:

```powershell
.\scripts\check-health.ps1
```

It checks all expected containers, FastAPI, Label Studio, MinIO, MLflow, PostgreSQL readiness, authenticated Redis connectivity, and the completed MinIO bucket initializer. The command exits with code `1` if a required check fails.

### 4. Open the local applications

- FastAPI documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- FastAPI health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Label Studio: [http://localhost:8080](http://localhost:8080)
- MinIO Console: [http://localhost:9001](http://localhost:9001)
- MLflow: [http://localhost:5000](http://localhost:5000)

All FastAPI routes except `/api/v1/health` require HTTP Basic authentication. Use the `API_USERNAME` and `API_PASSWORD` values from `.env`; the **Authorize** button in FastAPI Docs accepts these credentials. Label Studio also permits a local user to register at [http://localhost:8080/user/signup/](http://localhost:8080/user/signup/).

## Run the web client

The `frontend/` directory contains the Next.js web workspace and the skin-tracking UI prototype. It runs separately from the Docker Compose stack.

Open a PowerShell window from the repository root:

```powershell
Set-Location frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The Next.js pages are a UI prototype and do not yet connect to the API. See [frontend/README.md](frontend/README.md) for the available routes and commands.

## Typical workflow

1. Create a consent record with `POST /api/v1/consents`.
2. Use the returned pseudonymous `user_id` to submit an image at `POST /api/v1/analyses/users/{user_id}`.
3. Create generic training jobs at `POST /api/v1/training/runs` or inference jobs at `POST /api/v1/inference/runs`.
4. Poll the corresponding run endpoint for its state.
5. Use Label Studio for human-managed annotation. Add `LABEL_STUDIO_API_KEY` to `.env` only when the backend needs SDK access.

The OpenAPI page documents request and response schemas for each API route.

## Model workspace

The repository reserves model-package directories without placing implementation code or model artifacts in them:

```text
models/
├── time-series/
│   └── modelx/
└── non-time-series/
    └── u-net/
```

Do not commit datasets, checkpoints, weights, generated artifacts, or MLflow outputs. Store operational artifacts in MinIO through MLflow. See [models/README.md](models/README.md) for the policy.

The supported platform model families are `time_series`, `tabular`, and `image_segmentation`. The `models/` paths are reserved workspace locations, not a claim that a deployable model is already present.

## Logs

Docker uses local log rotation for every service: 10 MB per file, retaining five files. This is local log capture only; no Grafana, Prometheus, Loki, Tempo, OpenTelemetry, or other observability platform is included.

Save a timestamped snapshot of all service logs:

```powershell
.\scripts\export-logs.ps1
```

Stream recent logs from all services:

```powershell
.\scripts\export-logs.ps1 -Follow
```

Log snapshots are written under `logs/` and ignored by Git. You can also inspect a single service directly:

```powershell
docker compose logs --tail 200 api
docker compose logs --tail 200 inference-worker
docker compose logs --tail 200 trainer-worker
```

## Common commands

```powershell
# Stop containers while keeping the named volumes and their local data.
docker compose down

# Restart after a configuration or Compose change.
docker compose up -d --build

# Follow one service's output.
docker compose logs -f api

# Run tests locally when Python 3.11+ and project dependencies are installed.
python -m pytest

# Run linting locally.
ruff check .
```

To remove all local containers **and persisted PostgreSQL, Redis, MinIO, and Label Studio data**, run `docker compose down -v`. This is destructive and is only appropriate when you intentionally want a clean local environment.

## Safety and scope

- Aphrodize is an orchestration and MLOps foundation, not a medical device or diagnostic system.
- It does not implement face recognition, age prediction, diagnosis, causal claims, treatment recommendations, or automatic use of user inference data for training.
- User data and artifacts are intended for private MinIO storage and must not be included in logs or committed to Git.
- A reviewed, validated model artifact is required before inference can produce a result.
- The current Compose stack deliberately excludes external observability and monitoring systems.

## Further documentation

- [Implementation architecture](docs/architecture.md)
- [Project overview](docs/Aphrodize.md)
- [Product and scope](docs/Product%20and%20Scope.md)
- [AI and data](docs/AI%20and%20Data.md)
- [System and MLOps](docs/System%20and%20MLOps.md)
- [Safety and governance](docs/Safety%20and%20Governance.md)
