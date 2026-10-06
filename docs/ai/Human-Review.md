# Human review and model deployment

## Daily Health operator boundary

The following existing paths now require configured `ADMIN_USERNAME` and
`ADMIN_PASSWORD` HTTP Basic credentials, not the shared API credentials:

- `GET /api/v1/daily-health/model-versions`
- `GET /api/v1/daily-health/model-deployment`
- `GET /api/v1/daily-health/model-deployment/events`
- `PUT /api/v1/daily-health/model-deployment`
- `POST /api/v1/daily-health/model-deployment/rollback`

Keep the admin credential pair distinct from the service API pair. Missing admin
configuration or identical pairs fail closed. Prediction and user-owned health
routes keep their existing authentication. Do not put admin credentials in browser
code, public environment variables, URLs, or logs.

Training still produces review-only candidates. An operator inspects participant
and temporal holdout metrics, baseline comparisons, consent/data provenance and
limitations before submitting an approval reason. Existing artifact integrity
and quality gates remain mandatory; this change does not deploy a model.

Promotion and rollback audit events record the authenticated admin username as
`actor`, alongside version, action, reason and timestamp. The request cannot
supply an actor. Older events and system-generated events retain null actors;
they must be displayed as legacy/system rather than attributed to a person.
The existing startup schema upgrade adds the nullable column without replacing
stored history. Restart the updated API before using the new endpoints.

This identifies an authenticated operator account, not an individual behind a
shared admin login. Use dedicated operator identity/SSO and role-based permissions
before a multi-reviewer production deployment. No model-review UI is added here.

## Image review boundary

Label Studio review remains optional and requires separate annotation consent.
An analysis result is experimental and is not human-reviewed merely because a
review task exists. No automatic annotation-to-training bridge is introduced.
The image trainer still accepts only approved, licensed external datasets.
Using user annotations for training requires an explicit training-use policy,
appropriate consent, reviewed dataset versions and a separate approval workflow.

## UV review boundary

UV candidate generation still does not promote automatically. Explicit operator
promotion/rollback and the existing quality gates remain unchanged.

## Unified experiment tracking

Daily Health ARQ training now logs aggregate holdout metrics and cohort counts to
the `daily-health-next-day` MLflow experiment and records `mlflow_run_id` on the
candidate registry entry. No individual observations, participant IDs, or copies
of health-model artifacts are sent to MLflow. Consent gates and local artifact
cleanup remain unchanged. An MLflow outage leaves the candidate intact, surfaces
a worker failure, and leaves its run link empty; retry that worker job after
restoring tracking. Existing candidates are not backfilled automatically.

Generic `time_series`/`tabular` training responses explicitly expose
`execution_kind=metadata_only`; image training exposes `model_training`.
Metadata-only runs carry matching MLflow tags and must not be presented as fit
models or ready for deployment.

UV defaults to the shared MLflow server in Compose, with MinIO S3 credentials
available to the UV training client. Start with both `ai` and `uv-training`
profiles; standalone scripts default to `http://localhost:5000` and may override
the tracking URI explicitly. Existing file-store experiments are not migrated.
Rebuild/restart the trainer and UV training service and restart the updated API
to apply these changes. No training, refresh or promotion is triggered by editing
this configuration.
