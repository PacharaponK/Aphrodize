# Aphrodize backend

Python 3.11+ FastAPI application. Run commands from the repository root so `backend` imports and root `tests/` resolve. Prefer the locked Python 3.11 environment for reproducibility.

## Start locally

Follow the [root setup](../README.md) to create `.env` and start Docker:

```powershell
docker compose up -d --build
curl.exe --fail http://localhost:8000/api/v1/health
```

Enable `docker compose --profile ai up -d --build` for image storage, inference/training workers, Label Studio, and MLflow. Install the [required model files](../ai/README.md) before expecting successful image results. The base PostgreSQL and Redis ports are internal; a host Uvicorn process cannot connect to them without additional port/network configuration. The default API container already reloads mounted `backend/` source.

Open <http://localhost:8000/docs>. Database tables are created by the application startup path; use the documented deployment workflow for existing production databases rather than treating startup as a schema migration system.

## Authentication

| Operation | Credentials |
| --- | --- |
| Liveness and account signup/login | See each public OpenAPI operation |
| Service operations such as generic jobs and UV | Basic `API_USERNAME` / `API_PASSWORD` |
| Account-owned records | Bearer access token, matching the requested user |
| Product administration and model review | Basic `ADMIN_USERNAME` / `ADMIN_PASSWORD` |

Admin access requires configured credentials and a password of at least eight characters. Model reviewers must use credentials distinct from service credentials. See [deps.py](api/deps.py) and the [router](api/v1/router.py) for actual dependencies. Do not assume that one authorization scheme applies to every route. Frontend service secrets remain on the Next.js server.

## Code map

| Directory | Responsibility |
| --- | --- |
| `api/v1/routes/`, `api/schemas/` | HTTP handling and request/response validation |
| `services/` | Workflows, consent, recommendation rules, model lifecycle |
| `core/db/` | ORM models, async SQLAlchemy sessions |
| `libs/` | Storage, model loading, external integrations |
| `workers/` | ARQ inference and training consumers |
| `scripts/` | Bucket initialization, fixtures, annotation setup, controlled imports |
| `wrinkle/` | Separate synchronous research API adapter; [AI guide](../ai/README.md) |

Long-running inference/training belongs in workers. Redis jobs carry identifiers; workers fetch private inputs from MinIO. Training creates candidates, while deployment needs explicit review. Preserve separate analysis, annotation, and training consent.

## Fixtures and checks

```powershell
# Optional local demo account; do not load it into production.
docker compose --profile demo run --rm fixture

# Reviewed products only; requires the running API container.
docker compose exec -T api python -m backend.scripts.load_fixtures --products /app/backend/fixtures/products.yaml

# Locked backend test environment, separate from AI research dependencies.
uv sync --python 3.11 --locked --no-default-groups --group ci --no-install-package opencv-python
uv run --no-sync python -m pytest
uv run --no-sync ruff check backend tests
```

Inspect errors with `docker compose logs --tail 100 api` and `docker compose --profile ai logs --tail 100 inference-worker trainer-worker`. Restart workers after mounted source changes; recreate services with `up -d` after `.env` changes. A healthy API does not certify inference readiness or fresh UV data.

See the [documentation index](../docs/README.md) for endpoint workflows, schema diagrams, data deletion, candidate approval, and deployment. Keep secrets, image payloads, and health records out of logs and Git.
