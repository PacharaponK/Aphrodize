# Backend workspace

- This directory is the Python 3.11+ FastAPI application. Run Python commands from the repository root so `backend` imports and `tests/` resolve correctly.
- Register versioned endpoints in `api/v1/router.py`; keep HTTP validation and response handling in `api/v1/routes/` and `api/schemas/`, workflow logic in `services/`, persistence in `core/db/`, integrations in `libs/`, and queued work in `workers/`.
- Reuse the existing async SQLAlchemy session and ARQ queues. Keep long-running inference and training out of request handlers; queue identifiers, then let workers load private inputs from MinIO.
- Apply the route's appropriate Basic, admin, or user-token dependency. Check consent before accessing or using personal data, and preserve separate analysis, annotation, and training consent. Validate uploads before storage or queueing.
- Keep photos, health data, credentials, and model artifacts out of logs and Git. Preserve cleanup and expiry behavior for stored images. Never present model output as diagnosis or treatment advice.
- Add or update a focused test in the root `tests/` for changed behavior. Run `python -m pytest` for affected tests and `ruff check backend tests`; use the root `pyproject.toml` for configured tooling.
- See the root `README.md` and `docs/architecture/README.md` for service setup and data flow.
