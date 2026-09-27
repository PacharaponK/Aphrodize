"""Keep consented review images and Label Studio tasks in sync."""

import asyncio
import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.db.models import Analysis, AnnotationTask, Consent
from backend.libs.labelstudio_client import get_label_studio_client
from backend.libs.minio_client import annotation_image_key, get_bytes, put_bytes, remove_objects

ANNOTATION_CONSENT_VERSION = "image-annotation-v1"
ANNOTATION_RETENTION_DAYS = 30


async def has_annotation_consent(session: AsyncSession, user_id: UUID) -> bool:
    return await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == ANNOTATION_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .with_for_update()
    ) is not None


async def stage_annotation(
    session: AsyncSession, analysis: Analysis, aligned_face: bytes | None, redis: object
) -> None:
    if not settings.label_studio_project_id or not settings.label_studio_api_key:
        return
    if not await has_annotation_consent(session, analysis.user_id):
        return
    if not aligned_face:
        raise ValueError("Aligned review image is missing")
    key = annotation_image_key(analysis.user_id, analysis.id)
    row = AnnotationTask(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        object_key=key,
        expires_at=datetime.now(UTC) + timedelta(days=ANNOTATION_RETENTION_DAYS),
    )
    await asyncio.to_thread(put_bytes, key, aligned_face, "image/png", settings.annotation_bucket)
    try:
        session.add(row)
        await session.commit()
    except Exception:
        await asyncio.to_thread(remove_objects, [key], settings.annotation_bucket)
        raise
    await redis.enqueue_job("publish_annotation_task", str(row.id), _queue_name="inference")
    await redis.enqueue_job(
        "expire_annotation_task", str(row.id), _queue_name="inference", _defer_until=row.expires_at
    )


def _existing_task_id(client: object, analysis_id: UUID) -> int | None:
    # ponytail: scan one review project; filter server-side when task volume grows.
    for task in client.tasks.list(project=settings.label_studio_project_id):
        if task.data.get("analysis_id") == str(analysis_id):
            return int(task.id)
    return None


def _publish(row: AnnotationTask) -> int:
    client = get_label_studio_client()
    if client is None:
        raise RuntimeError("Label Studio is not configured")
    existing = _existing_task_id(client, row.analysis_id)
    if existing is not None:
        return existing
    # ponytail: inline images suit pilots; use external storage at higher volume.
    image = base64.b64encode(get_bytes(row.object_key, settings.annotation_bucket)).decode("ascii")
    task = client.tasks.create(
        project=settings.label_studio_project_id,
        data={
            "image": f"data:image/png;base64,{image}",
            "analysis_id": str(row.analysis_id),
        },
    )
    return int(task.id)


async def publish_annotation(session: AsyncSession, row: AnnotationTask) -> None:
    if row.label_studio_task_id is not None:
        return
    if datetime.now(UTC) >= row.expires_at or not await has_annotation_consent(
        session, row.user_id
    ):
        await delete_annotation(session, row)
        return
    row.label_studio_task_id = await asyncio.to_thread(_publish, row)
    await session.commit()
    if not await has_annotation_consent(session, row.user_id):
        await delete_annotation(session, row)


def _delete_remote(row: AnnotationTask) -> None:
    client = get_label_studio_client()
    if client is None:
        raise RuntimeError("Label Studio is not configured")
    task_id = row.label_studio_task_id or _existing_task_id(client, row.analysis_id)
    if task_id is None:
        return
    try:
        client.tasks.delete(id=str(task_id))
    except Exception as error:
        if getattr(error, "status_code", None) != 404:
            raise


async def delete_annotation(session: AsyncSession, row: AnnotationTask) -> None:
    await asyncio.to_thread(remove_objects, [row.object_key], settings.annotation_bucket)
    await asyncio.to_thread(_delete_remote, row)
    await session.delete(row)
    await session.commit()


async def delete_user_annotations(session: AsyncSession, user_id: UUID) -> None:
    rows = (
        await session.scalars(select(AnnotationTask).where(AnnotationTask.user_id == user_id))
    ).all()
    for row in rows:
        await delete_annotation(session, row)
