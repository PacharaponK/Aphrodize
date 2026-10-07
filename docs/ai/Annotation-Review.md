# Wrinkle annotation review

This workflow is for human review of consented, aligned face images. It does not train a model or treat model masks as ground truth.

## Set up once

1. Start the Compose stack and create a Label Studio API token. Put it in `.env` as `LABEL_STUDIO_API_KEY` and restart `api` and `inference-worker` so they receive it.
2. Run `docker compose exec api python -m backend.scripts.setup_annotation_project`. Copy the printed `LABEL_STUDIO_PROJECT_ID` to `.env`, then restart `api` and `inference-worker` again.
3. Test one task in the labeling UI before collecting user images. The worker puts each consented image in the private `aphrodize-annotation` MinIO bucket, then sends it directly to the Label Studio task as an inline image. No S3 source storage connection or private-network exception is needed. This is intended for a small review pilot; move task images to external storage if task volume makes the Label Studio project slow.

## Review rules

- The image is the aligned face used by the wrinkle model. Mark visible wrinkle pixels with the `Wrinkle` brush; leave other pixels unmarked.
- Skip an image if it is blurry, occluded, incorrectly aligned, or cannot be labeled reliably. Do not infer a clinical diagnosis.
- A model-generated mask, if added later, is only a suggestion. Human annotations are the review result.
- Do not copy images, names, or answers into comments or logs.

The optional capture checkbox creates a separate `image-annotation-v1` consent for that upload. Only successful analyses with active annotation consent are staged. The aligned image and Label Studio task are scheduled for deletion after 30 days. The capture page can revoke review consent for images submitted from the same browser during that period. `DELETE /api/v1/consents/users/{user_id}/annotations` revokes one user's review consent and removes review data; `DELETE /api/v1/users/{user_id}/images` includes the same cleanup. If Label Studio is unavailable during deletion, the image is removed first and the API returns 503; retry the request after Label Studio recovers. The worker also retries pending cleanup hourly. This browser-only revocation control is provisional until the app has user accounts.

No annotation is automatically exported or used for training. Export and dataset approval belong to the next development phase.


## VM and Windows GPU deployment

The VM runs the pinned Label Studio release using the `annotation` Compose profile.
Open `https://<VM_HOST>/label-studio/`; reviewer credentials are kept in the VM's
private `.env` (`LABEL_STUDIO_USERNAME` and `LABEL_STUDIO_PASSWORD`). Public signup
is disabled. Caddy strips the URL prefix before forwarding to Label Studio, while
`LABEL_STUDIO_HOST` generates links with the public prefix. The backend uses the
internal `http://label-studio:8080` URL. Keep the Label Studio named volume: it holds
the reviewer account, project configuration and annotations.

```bash
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml -f compose.duckdns.yml --profile annotation up -d label-studio api
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml -f compose.duckdns.yml --profile annotation up -d --no-deps --force-recreate caddy
```

Recreate Caddy after updating its Caddyfile so the existing container mounts and
loads the new Label Studio route.

Set `LABEL_STUDIO_API_KEY` and `LABEL_STUDIO_PROJECT_ID` in the private VM `.env`.
The startup token uses Label Studio's explicitly enabled legacy-token support;
never place it in browser code or Git. The `Aphrodize wrinkle mask review` project
uses the existing `Wrinkle` brush configuration from `setup_annotation_project.py`.

The remote GPU worker must receive the same project and token. Its
`compose.gpu.yml` no longer overrides them with an empty token and project zero.
The VM prepares `.env.annotation.gpu` with only the three Label Studio settings,
using the public HTTPS URL for Windows. In the existing Windows GPU runtime folder:

```powershell
scp aphrodize@172.30.81.237:~/Aphrodize/scripts/enable-annotation-gpu.ps1 .
powershell -ExecutionPolicy Bypass -File .\enable-annotation-gpu.ps1
```

This script preserves model paths and data-service credentials, updates review
settings, restarts the existing worker image, and checks access to the project.
It does not rebuild the model. Keep `.env.gpu` and `.env.annotation.gpu` private.
After it reports `GPU worker -> Label Studio: OK`, test a newly consented upload:
`completed` analysis -> private aligned image -> queued publish -> Label Studio task.
Only separately consented successful analyses enter review. Review consent does not
permit model training. Revocation deletes both the review copy and the remote task;
retention remains 30 days. Old uploads without review consent are not backfilled.
