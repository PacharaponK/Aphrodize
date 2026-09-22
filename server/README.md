# Aphrodize backend

Phase 6 provides a FastAPI adapter for the FFHQ-Wrinkle research pipeline.

Run it from the repository root with the dedicated environment:

```powershell
conda run -n ffhq-wrinkle python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`
- `POST /v1/wrinkle/analyze` as multipart form data with `image` and
  `consent_accepted=true`

The default confidence policy is intentionally `not_calibrated`, so analysis
returns `status=abstained` and withholds derived scores and recommendations.
Raw probability maps and masks remain temporary and are never returned as
public URLs.

After an approved target-user calibration run, point the service at the
released policy bundle before startup:

```powershell
$env:APHRODIZE_WRINKLE_POLICY_BUNDLE = "C:\path\to\approved-policy-bundle"
```

The bundle must contain a matching `candidate_confidence_policy.json` and a
passed `calibration_report.json`. Without it, the service keeps the fail-closed
default policy.
