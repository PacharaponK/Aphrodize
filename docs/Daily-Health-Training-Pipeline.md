# Daily-health data and model-versioning flow

## Persisted data

- `daily_health_entries` stores the user's daily input, calculated sleep-duration score, and a separate copy of prediction output. A `(user_id, local_date)` upsert keeps one current entry per user and date.
- `daily_health_outcomes` stores values the user reports they actually observed (energy, thirst, and skin-dryness scores). These are kept separate from predictions.
- `daily_health_dataset_records` is a provenance-tagged archive for imported CSV snapshots. It keeps a file fingerprint and row number, replaces external identifiers with dataset-local participant aliases, and marks every imported row ineligible for user-model training. The CSV importer accepts an explicit field allowlist and rejects unknown columns so arbitrary PII headers cannot be archived.
- `daily_health_model_versions` is the registry for user-trained candidate artifacts and their validation/test metrics. `daily_health_model_deployments` stores the explicitly approved active/previous version, while `daily_health_model_deployment_events` records promotion, rollback, and erasure actions.

The PostgreSQL data volume is the durable database. Do not run `docker compose down -v` unless you intentionally want to erase all local application data.

## Initial dataset snapshot

The selected CSV is `sandboxes/datamake/output/lifestyle_medically_cautious_sleepmax540_forecast_with_real_user.csv`. It currently contains 1,234 rows: 14 rows attributed to `real_user_tracker_xlsx` and 1,220 synthetic rows. The observed rows have a categorical/decimal `skin_dryness_level` field and skin-feeling labels, but no numeric thirst/dryness scores on the model's 0–10 scale. The synthetic 0–10 values were generated from rules. The importer therefore retains all of the data and its provenance but excludes every imported row from model training; it does not infer or convert target scores.

Once the PostgreSQL service is running, import this snapshot with:

```powershell
docker compose run --rm --no-deps `
  --volume 'C:/Users/ACER/Desktop/Projects/Aphrodize/sandboxes/datamake/output/lifestyle_medically_cautious_sleepmax540_forecast_with_real_user.csv:/app/seed.csv:ro' `
  api python -m backend.scripts.import_daily_health_dataset /app/seed.csv
```

The import is idempotent for an unchanged file fingerprint. Editing the CSV creates a new snapshot instead of overwriting the previous one. To remove one complete imported snapshot, use `python -m backend.scripts.delete_daily_health_dataset_snapshot <sha256> --confirm` after verifying its exact fingerprint. Imported snapshots are not linked to an authenticated account, so this is whole-snapshot deletion rather than per-person deletion.

## Consent and labels

Saving a daily entry requires the existing consent to store daily health data. Model training is a separate, optional consent (`daily-health-model-training-v1`). The user can revoke it; daily history remains stored, the consent becomes inactive, unapproved candidates are marked stale, and no further data from the user enters training. An already-approved model is not retroactively unlearned by opt-out alone. Users who have not opted in are excluded from the training query.

The self-report form records numeric 0–10 thirst and dryness scores separately from predictions. A training example is created only when both are supplied, a previous day's user-reported lifestyle entry exists, and the user has active model-training consent. The target day's actual reports are paired with that user's previous-day inputs, so the candidate predicts next-day thirst/dryness. Predicted scores, synthetic rows, and imported categorical observations are never used as ground truth.

## Candidate training and versioning

After an opted-in user submits both self-reported scores, the API checks readiness and queues the trainer worker only when there are at least 100 complete next-day examples from at least 5 opted-in participants. A new candidate is considered after at least 25 more examples than the most recent candidate (or if consent withdrawal means a new snapshot has fewer rows). The outcome save still succeeds if Redis is unavailable; a missed trigger can be retried by submitting a later complete self-report.

The worker:

1. Re-reads the current active-consent cohort from PostgreSQL.
2. Splits by participant (60/20/20 train/validation/test), preventing a person's days from leaking across partitions.
3. Fits a multi-output `RandomForestRegressor` only on the train partition and reports MAE, RMSE, and R² where defined for validation and untouched test users.
4. Writes a model and manifest under `models/time-series/non-linear-model/artifacts/user-candidates/<version-id>/` and stores the candidate status, data fingerprint, sample counts, and metrics in `daily_health_model_versions`.

Candidate versions are not automatically promoted. Review recent versions with `GET /api/v1/daily-health/model-versions`, inspect the active pointer with `GET /api/v1/daily-health/model-deployment`, and explicitly promote a candidate with `PUT /api/v1/daily-health/model-deployment` plus a written reason. The endpoint validates the artifact checksum and manifest before changing the active pointer. Inference uses the approved one-day-ahead candidate and identifies its version and target date; when no candidate is active, the source-controlled same-day baseline remains active. A broken active artifact returns unavailable rather than silently falling back. Rollback is explicit via `POST /api/v1/daily-health/model-deployment/rollback`; promotion, rollback, and erasure events can be inspected with `GET /api/v1/daily-health/model-deployment/events`. Metrics describe agreement with self-reported scores, not clinical accuracy or diagnosis. There is no candidate yet from the imported snapshot because it is excluded and the required volume of consented numeric outcomes has not been reached.

## User-requested erasure and retention

The explicit `DELETE /api/v1/daily-health/users/{user_id}/data` action deletes that account's daily entries, self-reported outcomes, profile/age/menstrual context, and revokes the associated consents. Since model-version records do not retain per-user cohort membership, erasure removes the user-trained model registry and version-bearing deployment history, clears the active pointer, and removes generated user-candidate artifacts from the exact allowlisted model directory. A single erasure audit event without a user or model-version ID remains. This conservatively resets serving to the baseline. Artifact cleanup only unlinks the known `model.joblib` and `manifest.json` files in generated direct-child version folders; unexpected files or symlinks stop cleanup for operator review. The browser clears its daily-health session so the user can start again only after a new storage consent.

No automatic retention period is configured. Operators should define a retention duration with the product/privacy owner rather than assume a default. Imported snapshots are separate from account-linked records and require whole-snapshot deletion by fingerprint.
