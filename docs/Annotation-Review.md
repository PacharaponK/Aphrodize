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
