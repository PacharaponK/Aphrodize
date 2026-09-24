import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from arq.connections import RedisSettings

from backend.core.db.models import Analysis, AnalysisStatus, InferenceRun
from backend.core.db.session import SessionLocal, close_database
from backend.libs.minio_client import (
    analysis_artifact_key,
    get_bytes,
    put_bytes,
    remove_objects,
)
from backend.libs.redis_client import redis_settings

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    from backend.wrinkle.service import WrinkleAnalysisService

    ctx["wrinkle_service"] = WrinkleAnalysisService(
        released_policy_bundle=os.environ.get("APHRODIZE_WRINKLE_POLICY_BUNDLE")
    )


async def shutdown(_: dict) -> None:
    await close_database()


async def run_inference(ctx: dict, analysis_id: str) -> None:
    async with SessionLocal() as session:
        analysis = await session.get(Analysis, UUID(analysis_id))
        if analysis is None or analysis.status != AnalysisStatus.queued:
            return
        analysis.status = AnalysisStatus.running
        await session.commit()

        uploaded: list[str] = []
        try:
            try:
                payload = await asyncio.to_thread(get_bytes, analysis.object_key)
                suffix = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                }.get(analysis.content_type, ".jpg")
                artifacts: dict[str, bytes] = {}
                response = await asyncio.to_thread(
                    ctx["wrinkle_service"].analyze_bytes,
                    payload,
                    suffix,
                    artifact_sink=artifacts.update,
                )
                for kind in ("overlay", "mask"):
                    key = analysis_artifact_key(analysis.user_id, analysis.id, kind)
                    await asyncio.to_thread(put_bytes, key, artifacts[kind], "image/png")
                    uploaded.append(key)
                expires_at = datetime.now(UTC) + timedelta(hours=24)
                job = await ctx["redis"].enqueue_job(
                    "expire_analysis_artifacts",
                    str(analysis.user_id),
                    str(analysis.id),
                    _queue_name="inference",
                    _defer_until=expires_at,
                )
                if job is None:
                    raise RuntimeError("artifact expiry job was not queued")
            except Exception as error:
                from ai.ffhq_wrinkle.quality import QualityGateError

                if uploaded:
                    try:
                        await asyncio.to_thread(remove_objects, uploaded)
                    except Exception:
                        logger.exception(
                            "Could not remove incomplete artifacts for %s", analysis.id
                        )
                if isinstance(error, QualityGateError):
                    analysis.status = AnalysisStatus.rejected
                    analysis.error_category = "image_quality"
                    analysis.quality_flags = list(error.assessment.issues)
                    analysis.result = {
                        "status": "rejected",
                        "quality_flags": analysis.quality_flags,
                    }
                else:
                    logger.exception("Wrinkle inference failed for analysis %s", analysis.id)
                    analysis.status = AnalysisStatus.failed
                    analysis.error_category = "inference_failed"
                    analysis.result = {"message": "Wrinkle inference failed."}
            else:
                analysis.status = AnalysisStatus.completed
                analysis.error_category = None
                analysis.result = response.model_dump(mode="json")
                analysis.result["analysis_id"] = str(analysis.id)
                analysis.result["artifacts_expires_at"] = expires_at.isoformat()

            analysis.completed_at = datetime.now(UTC)
            await session.commit()
        finally:
            try:
                await asyncio.to_thread(remove_objects, [analysis.object_key])
            except Exception:
                logger.exception("Could not remove source image for %s", analysis.id)


async def expire_analysis_artifacts(_: dict, user_id: str, analysis_id: str) -> None:
    keys = [
        analysis_artifact_key(UUID(user_id), UUID(analysis_id), kind)
        for kind in ("overlay", "mask")
    ]
    await asyncio.to_thread(remove_objects, keys)


async def run_model_inference(_: dict, inference_run_id: str) -> None:
    """Fail closed until model loading, signature validation, and approval policy exist."""
    async with SessionLocal() as session:
        run = await session.get(InferenceRun, UUID(inference_run_id))
        if run is None or run.status != "queued":
            return
        run.status = "failed"
        run.error_category = "model_not_deployed"
        run.result = {"message": "No approved model deployment is available for this model URI."}
        run.completed_at = datetime.now(UTC)
        await session.commit()


class WorkerSettings:
    functions = [run_inference, run_model_inference, expire_analysis_artifacts]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings: RedisSettings = redis_settings()
    queue_name = "inference"
    # ponytail: one model job at a time; raise after measuring worker memory and latency.
    max_jobs = 1
