"""Keep consented review images and Label Studio tasks in sync."""

import asyncio
import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.db.models import Analysis, AnnotationTask, Consent
from backend.core.observability import enqueue_job
from backend.libs.labelstudio_client import get_label_studio_client
from backend.libs.minio_client import annotation_image_key, get_bytes, put_bytes, remove_objects

ANNOTATION_CONSENT_VERSION = "image-annotation-v1"
ANNOTATION_RETENTION_DAYS = 30


async def has_annotation_consent(session: AsyncSession, user_id: UUID) -> bool:
    # Lock the active consent row while a publish or delete operation checks it.
    return await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == ANNOTATION_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .with_for_update()
    ) is not None


# Stage a separate aligned image only when review consent is still active.
async def stage_annotation(
    session: AsyncSession, analysis: Analysis, aligned_face: bytes | None, redis: object
) -> None:
    # Skip the entire review branch when the integration is not configured.
    if not settings.label_studio_project_id or not settings.label_studio_api_key:
        return
    # Analysis consent alone is insufficient for human review.
    if not await has_annotation_consent(session, analysis.user_id):
        return
    # The image must be the aligned face produced by the successful AI pipeline.
    if not aligned_face:
        raise ValueError("Aligned review image is missing")
    # Keep review images under a per-user, per-analysis key.
    key = annotation_image_key(analysis.user_id, analysis.id)
    # The row tracks the image, remote task ID, and 30-day deletion deadline.
    row = AnnotationTask(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        object_key=key,
        expires_at=datetime.now(UTC) + timedelta(days=ANNOTATION_RETENTION_DAYS),
    )
    # Store the image in the private review bucket before committing its row.
    await asyncio.to_thread(put_bytes, key, aligned_face, "image/png", settings.annotation_bucket)
    try:
        session.add(row)
        await session.commit()
    except Exception:
        # Avoid an orphan image when the database commit fails.
        await asyncio.to_thread(remove_objects, [key], settings.annotation_bucket)
        raise
    # Publish asynchronously; the user analysis result is already committed.
    await enqueue_job(redis, "publish_annotation_task", str(row.id), _queue_name="inference")
    # A delayed job removes the review copy and remote task after retention ends.
    await enqueue_job(redis,
        "expire_annotation_task", str(row.id), _queue_name="inference", _defer_until=row.expires_at
    )


def _existing_task_id(client: object, analysis_id: UUID) -> int | None:
    # ponytail: scan one review project; filter server-side when task volume grows.
    for task in client.tasks.list(project=settings.label_studio_project_id):
        # Matching on analysis ID makes a retried publish idempotent.
        if task.data.get("analysis_id") == str(analysis_id):
            return int(task.id)
    return None


def _publish(row: AnnotationTask) -> int:
    # Create the SDK client only for a configured Label Studio token.
    client = get_label_studio_client()
    if client is None:
        raise RuntimeError("Label Studio is not configured")
    existing = _existing_task_id(client, row.analysis_id)
    if existing is not None:
        # The remote task may exist even if its ID was not committed locally.
        return existing
    # ponytail: inline images suit pilots; use external storage at higher volume.
    # Embed image bytes in the task so Label Studio needs no private MinIO access.
    image = base64.b64encode(get_bytes(row.object_key, settings.annotation_bucket)).decode("ascii")
    task = client.tasks.create(
        project=settings.label_studio_project_id,
        data={
            "image": f"data:image/png;base64,{image}",
            "analysis_id": str(row.analysis_id),
        },
    )
    # Persist only the remote ID in PostgreSQL, not a second image copy.
    return int(task.id)


async def publish_annotation(session: AsyncSession, row: AnnotationTask) -> None:
    # Recheck consent and expiry because publishing may run long after staging.
    if row.label_studio_task_id is not None:
        # This local row already records a completed publish.
        return
    if datetime.now(UTC) >= row.expires_at or not await has_annotation_consent(
        session, row.user_id
    ):
        # Remove expired or revoked work instead of publishing it.
        await delete_annotation(session, row)
        return
    # Run the synchronous SDK call off the async worker event loop.
    row.label_studio_task_id = await asyncio.to_thread(_publish, row)
    await session.commit()
    # Handle a consent revocation that raced with remote task creation.
    if not await has_annotation_consent(session, row.user_id):
        await delete_annotation(session, row)


def _delete_remote(row: AnnotationTask) -> None:
    client = get_label_studio_client()
    if client is None:
        raise RuntimeError("Label Studio is not configured")
    # Fall back to an analysis-ID lookup if the local remote ID was never saved.
    task_id = row.label_studio_task_id or _existing_task_id(client, row.analysis_id)
    if task_id is None:
        return
    try:
        client.tasks.delete(id=str(task_id))
    except Exception as error:
        # A missing remote task already satisfies deletion; other errors must retry.
        if getattr(error, "status_code", None) != 404:
            raise


async def delete_annotation(session: AsyncSession, row: AnnotationTask) -> None:
    # Remove the private image first, then the remote task and local tracking row.
    await asyncio.to_thread(remove_objects, [row.object_key], settings.annotation_bucket)
    await asyncio.to_thread(_delete_remote, row)
    await session.delete(row)
    await session.commit()


async def delete_user_annotations(session: AsyncSession, user_id: UUID) -> None:
    # Revoke every review task created for this user, including pending publishes.
    rows = (
        await session.scalars(select(AnnotationTask).where(AnnotationTask.user_id == user_id))
    ).all()
    for row in rows:
        await delete_annotation(session, row)
