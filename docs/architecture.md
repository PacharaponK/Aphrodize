# Aphrodize implementation architecture

This implementation is a modular monolith with asynchronous model work. It intentionally does **not** include Grafana, Loki, Tempo, OpenTelemetry, Prometheus, or other observability components at this stage.

```text
Client
  -> FastAPI API
     -> PostgreSQL: consent, questionnaire, job metadata, results
     -> MinIO: private source images, derived artifacts, MLflow artifacts
     -> Redis / ARQ
          -> inference worker: approved image model workloads
          -> trainer worker: time-series, tabular, and segmentation training workflows
               -> MLflow: runs, parameters, metrics, model artifacts
     -> Label Studio SDK: explicit, human-managed annotation-project integration
```

## Services

| Service | Responsibility |
|---|---|
| FastAPI | Validates requests, captures consent, stores questionnaire data, invokes approved time-series model code, queues jobs, and exposes result APIs. |
| PostgreSQL / SQLAlchemy | Stores pseudonymous identifiers and all workflow metadata. |
| MinIO | Stores private images and future derived/model artifacts. Objects are never included in API logs. |
| Redis / ARQ | Separates API requests from inference and training work. `inference` and `training` use distinct queues. |
| Label Studio | Human-operated annotation UI. The API only enables SDK access when `LABEL_STUDIO_API_KEY` is configured. |
| MLflow | Stores reproducible training-run metadata and artifacts. User inference images are not training data. |

## Model families

`POST /api/v1/training/runs` accepts `time_series`, `tabular`, and `image_segmentation`. Image analyses use the checked FFHQ-Wrinkle model mounted read-only in the inference worker. `POST /api/v1/inference/runs` accepts generic `time_series` and `tabular` model URIs and still fails safe with `model_not_deployed` until an approved MLflow model is available. The trainer records an MLflow run but does not train on user uploads.

The model workspace lives in [`models/`](../models/README.md): `models/time-series/linear-model/` contains linear ordered-observation models, `models/time-series/non-linear-model/` is reserved for non-linear forecasting models, and `models/non-time-series/` contains image-model source and artifacts. Hyphenated taxonomy folders are loaded explicitly by [`backend/libs/model_loader.py`](../backend/libs/model_loader.py).

## Local start

```bash
cp .env.example .env
docker compose up --build
```

API documentation is at `http://localhost:8000/docs`; Label Studio is at `http://localhost:8080`; MinIO Console is at `http://localhost:9001`; MLflow is at `http://localhost:5000`.

Create consent before posting a questionnaire or an image. `POST /api/v1/consents` returns a pseudonymous `user_id`.

## Local credentials

Copy `.env.example` to `.env` and provide the local credentials before starting the stack. `.env` is ignored by Git. All API routes other than `/api/v1/health` require HTTP Basic authentication using `API_USERNAME` and `API_PASSWORD`; FastAPI Docs supports the **Authorize** control. PostgreSQL, Redis, MinIO, and Label Studio read their respective credentials from the same local file. Label Studio permits local user registration at `http://localhost:8080`. MLflow is internal to the Compose network and does not provide built-in user/password authentication in this initial stack.

The Compose stack uses MinIO's public Quay images. A one-time `minio-init` service waits for MinIO and creates the private application and MLflow artifact buckets with the official MinIO client image.

## Health checks

After starting the stack, run this from PowerShell at the repository root:

```powershell
.\scripts\check-health.ps1
```

It checks expected containers, PostgreSQL readiness, authenticated Redis access, MinIO's liveness endpoint, Label Studio's login route, MLflow's health endpoint, FastAPI's health endpoint, and the completed bucket-initialization job. It exits with code `1` if any required check fails.

## Local logs

To save the latest logs from all Compose services under [`logs/`](../logs/README.md), run:

```powershell
.\scripts\export-logs.ps1
```

Docker rotates each container's local logs at 10 MB and retains five files. This is local log capture only; no external log collector or observability service is deployed.
