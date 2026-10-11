# Image-review consent availability

The deployed API image lacked `/api/v1/capabilities`, although Label Studio
credentials and project 1 were configured and the SDK could read the project.
The frontend received 404 and correctly treated optional image review as
unavailable, disabling review and the dependent training opt-in.

Deployed an image derived from the running API, replacing only
`backend/api/v1/routes/health.py` with the existing repository implementation.
The deployment preserves the running Compose configuration, checks image
identity and service health, and automatically rolls back on failed checks.
Private deployment and rollback records are in
`.releases/annotation-capabilities-20261008/`.

Added a regression test that requests the endpoint through the registered
FastAPI application without credentials, supplementing the existing capability
configuration tests. Explicit consent, separate training opt-in, and revocation
behavior are unchanged.

Validation:

- Candidate-image consent tests: 16 passed; existing SDK deprecation warnings.
- Frontend capture/consent tests: 22 passed.
- Ruff on the capability route and consent tests: passed.
- Deployed API health and frontend capability checks: passed.
- Public `/api/analysis?consents=1`: HTTP 200 and
  `annotation_review_available: true`, with new-visitor consent false.
- Public `/capture`: HTTP 200.
- Interactive browser verification could not run: cached Chromium requires
  `libnspr4.so`, which is absent. No browser verification is claimed.
