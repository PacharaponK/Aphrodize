"""Move one queued photo through AI inference and persist only safe outputs.

The worker is the bridge between the platform stores (PostgreSQL, MinIO,
Redis) and the in-process FFHQ-Wrinkle pipeline in backend.wrinkle.service.
"""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from backend.core.db.models import Analysis, AnalysisStatus, AnnotationTask, InferenceRun
from backend.core.db.session import SessionLocal, close_database
from backend.core.observability import (
    enqueue_job,
    observed_job,
    secondary_failures,
    start_worker_metrics,
    stop_worker_metrics,
)
from backend.libs.minio_client import (
    analysis_artifact_key,
    get_bytes,
    put_bytes,
    remove_objects,
)
from backend.libs.redis_client import redis_settings
from backend.services.annotation_service import (
    delete_annotation,
    has_annotation_consent,
    publish_annotation,
    stage_annotation,
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Create one service per worker process so its model can stay in memory."""
    # Import here so the queue can start without loading AI code before startup.
    from ai.ffhq_wrinkle.confidence import load_confidence_policy
    from backend.wrinkle.service import WrinkleAnalysisService

    reviewed_policy_path = os.environ.get("APHRODIZE_WRINKLE_REVIEWED_POLICY") or None
    reviewed_policy = load_confidence_policy(reviewed_policy_path) if reviewed_policy_path else None
    if reviewed_policy is not None and reviewed_policy.status != "manually_approved":
        raise ValueError("reviewed policy must record manual approval")
    # A process-local service caches its model between analysis jobs.
    ctx["wrinkle_service"] = WrinkleAnalysisService(
        confidence_policy=reviewed_policy,
        released_policy_bundle=os.environ.get("APHRODIZE_WRINKLE_POLICY_BUNDLE") or None,
        approved_model_manifest=os.environ.get("APHRODIZE_WRINKLE_APPROVED_MANIFEST") or None,
    )
    await start_worker_metrics(ctx)


async def shutdown(ctx: dict) -> None:
    # Release database connections when ARQ stops this worker process.
    await stop_worker_metrics(ctx)
    await close_database()


@observed_job
async def run_inference(ctx: dict, analysis_id: str) -> None:
    """Turn a queued Analysis into a terminal result.

    The queue carries only the analysis ID. The image bytes come from MinIO,
    the AI response is stored as JSON in PostgreSQL, and only the two display
    PNGs are copied back to MinIO. Source bytes are removed in ``finally``.
    """
    # The Redis job contains only an ID; fetch status and storage key from DB.
    async with SessionLocal() as session:
        analysis = await session.get(Analysis, UUID(analysis_id))
        # Ignore missing jobs and jobs already handled by another worker.
        if analysis is None or analysis.status != AnalysisStatus.queued:
            ctx["telemetry_outcome"] = "skipped"
            return
        # Persist 'running' so API polling can show that work has started.
        analysis.status = AnalysisStatus.running
        await session.commit()

        # Remember each uploaded artifact so partial uploads can be removed.
        uploaded: list[str] = []
        try:
            try:
                # MinIO access is synchronous; a thread keeps the event loop free.
                payload = await asyncio.to_thread(get_bytes, analysis.object_key)
                # Preserve image encoding in the temporary upload filename.
                suffix = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                }.get(analysis.content_type, ".jpg")
                # The service calls artifacts.update with its two display PNGs.
                artifacts: dict[str, bytes] = {}
                # The sink receives PNG bytes while the service's temp files still exist.
                response = await asyncio.to_thread(
                    ctx["wrinkle_service"].analyze_bytes,
                    payload,
                    suffix,
                    artifact_sink=artifacts.update,
                )
                # Raw model arrays stay temporary; only these two PNGs are retained.
                for kind in ("overlay", "mask", "regions", "outline"):
                    if kind not in artifacts:
                        continue
                    # Derived keys belong to this user and analysis ID.
                    key = analysis_artifact_key(analysis.user_id, analysis.id, kind)
                    # Save only viewable PNGs, never uploaded photo or model arrays.
                    mime = "image/svg+xml" if kind == "outline" else "image/png"
                    await asyncio.to_thread(put_bytes, key, artifacts[kind], mime)
                    uploaded.append(key)
                # Both derived images have a 24-hour viewing lifetime.
                expires_at = datetime.now(UTC) + timedelta(hours=24)
                # The API also checks this timestamp, even if the delete job runs late.
                job = await enqueue_job(
                    ctx["redis"],
                    "expire_analysis_artifacts",
                    str(analysis.user_id),
                    str(analysis.id),
                    _queue_name="inference",
                    _defer_until=expires_at,
                )
                # A missing expiry job means we cannot safely retain artifacts.
                if job is None:
                    raise RuntimeError("artifact expiry job was not queued")
            except Exception as error:
                # Distinguish expected image rejection from an inference failure.
                from ai.ffhq_wrinkle.quality import QualityGateError

                if uploaded:
                    try:
                        # Roll back images already uploaded before the error.
                        await asyncio.to_thread(remove_objects, uploaded)
                    except Exception:
                        secondary_failures.labels("incomplete_artifact_cleanup").inc()
                        logger.exception(
                            "Could not remove incomplete artifacts for %s", analysis.id
                        )
                if isinstance(error, QualityGateError):
                    # This includes no/multiple faces and failed quality checks.
                    analysis.status = AnalysisStatus.rejected
                    analysis.error_category = "image_quality"
                    analysis.quality_flags = list(error.assessment.issues)
                    analysis.result = {
                        "status": "rejected",
                        "quality_flags": analysis.quality_flags,
                    }
                else:
                    # Keep internal exception details in logs, not public JSON.
                    logger.exception("Wrinkle inference failed for analysis %s", analysis.id)
                    analysis.status = AnalysisStatus.failed
                    analysis.error_category = "inference_failed"
                    analysis.result = {"message": "Wrinkle inference failed."}
            else:
                # A confidence abstention is still a successful inference run.
                analysis.status = AnalysisStatus.completed
                analysis.error_category = None
                # Pydantic response becomes JSON stored on the Analysis row.
                analysis.result = response.model_dump(mode="json")
                checkpoint_sha = analysis.result.get("model_output", {}).get("checkpoint_sha256")
                if checkpoint_sha:
                    analysis.model_version = checkpoint_sha
                # Use the database's stable ID instead of the service's new UUID.
                analysis.result["analysis_id"] = str(analysis.id)
                analysis.result["artifacts_expires_at"] = expires_at.isoformat()

            # Both successful and failed jobs receive a completion timestamp.
            analysis.completed_at = datetime.now(UTC)
            ctx["telemetry_outcome"] = {
                AnalysisStatus.completed: "succeeded",
                AnalysisStatus.failed: "failed",
                AnalysisStatus.rejected: "rejected",
            }[analysis.status]
            # Persist the user-facing result before starting optional review work.
            await session.commit()
            if analysis.status == AnalysisStatus.completed:
                # Review staging is a second workflow; its failure does not erase the user result.
                try:
                    await stage_annotation(
                        session, analysis, artifacts.get("aligned_face"), ctx["redis"]
                    )
                except Exception:
                    secondary_failures.labels("annotation_staging").inc()
                    logger.exception("Could not queue annotation review for %s", analysis.id)
        finally:
            try:
                # The original upload is deleted regardless of outcome.
                await asyncio.to_thread(remove_objects, [analysis.object_key])
            except Exception:
                secondary_failures.labels("source_cleanup").inc()
                logger.exception("Could not remove source image for %s", analysis.id)


@observed_job
async def expire_analysis_artifacts(_: dict, user_id: str, analysis_id: str) -> None:
    """Delete the two derived PNGs after their 24-hour viewing window."""
    # Reconstruct both private object keys from the IDs in the delayed job.
    keys = [
        analysis_artifact_key(UUID(user_id), UUID(analysis_id), kind)
        for kind in ("overlay", "mask", "regions", "outline")
    ]
    await asyncio.to_thread(remove_objects, keys)


@observed_job
async def publish_annotation_task(_: dict, task_id: str) -> None:
    # Resolve the staged row; annotation_service handles consent and remote idempotency.
    async with SessionLocal() as session:
        row = await session.get(AnnotationTask, UUID(task_id))
        if row is not None:
            await publish_annotation(session, row)


@observed_job
async def expire_annotation_task(_: dict, task_id: str) -> None:
    # Ignore an early delayed job; delete only after the stored deadline.
    async with SessionLocal() as session:
        row = await session.get(AnnotationTask, UUID(task_id))
        if row is not None and datetime.now(UTC) >= row.expires_at:
            await delete_annotation(session, row)


@observed_job
async def delete_annotation_task(_: dict, task_id: str) -> None:
    # A revoke job deletes only rows whose review consent is no longer active.
    async with SessionLocal() as session:
        row = await session.get(AnnotationTask, UUID(task_id))
        if row is not None and not await has_annotation_consent(session, row.user_id):
            await delete_annotation(session, row)


@observed_job
async def reconcile_annotation_tasks(ctx: dict) -> None:
    # Recover unpublished tasks and pending deletions after worker or Label Studio outages.
    async with SessionLocal() as session:
        # Inspect every staged row because a queue job may have been lost.
        rows = (await session.scalars(select(AnnotationTask))).all()
        for row in rows:
            try:
                if datetime.now(UTC) >= row.expires_at or not await has_annotation_consent(
                    session, row.user_id
                ):
                    # Retention expiry and revocation take precedence over publishing.
                    await delete_annotation(session, row)
                elif row.label_studio_task_id is None:
                    # Retry only work without a recorded remote task ID.
                    await publish_annotation(session, row)
            except Exception:
                ctx["telemetry_outcome"] = "failed"
                logger.exception("Could not reconcile annotation task %s", row.id)


@observed_job
async def run_model_inference(ctx: dict, inference_run_id: str) -> None:
    """Fail closed until model loading, signature validation, and approval policy exist."""
    async with SessionLocal() as session:
        run = await session.get(InferenceRun, UUID(inference_run_id))
        if run is None or run.status != "queued":
            ctx["telemetry_outcome"] = "skipped"
            return
        run.status = "failed"
        ctx["telemetry_outcome"] = "failed"
        run.error_category = "model_not_deployed"
        run.result = {"message": "No approved model deployment is available for this model URI."}
        run.completed_at = datetime.now(UTC)
        await session.commit()


class WorkerSettings:
    # ARQ dispatches these names from jobs written to the inference queue.
    functions = [
        run_inference,
        run_model_inference,
        expire_analysis_artifacts,
        publish_annotation_task,
        expire_annotation_task,
        delete_annotation_task,
    ]
    # Reconcile once at startup and again at the top of each hour.
    cron_jobs = [cron(reconcile_annotation_tasks, minute=0, run_at_startup=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings: RedisSettings = redis_settings()
    queue_name = "inference"
    # ponytail: one model job at a time; raise after measuring worker memory and latency.
    max_jobs = 1
    health_check_interval = 30
