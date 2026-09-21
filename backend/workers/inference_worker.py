from datetime import UTC, datetime
from uuid import UUID

from arq.connections import RedisSettings

from backend.core.db.models import Analysis, AnalysisStatus, InferenceRun
from backend.core.db.session import SessionLocal, close_database
from backend.libs.redis_client import redis_settings


async def startup(_: dict) -> None:
    return None


async def shutdown(_: dict) -> None:
    await close_database()


async def run_inference(_: dict, analysis_id: str) -> None:
    """Reserve the inference worker contract without fabricating medical-quality predictions.

    Mount a reviewed model artifact from MLflow and replace this status with real, validated
    regional results before exposing the feature to users.
    """
    async with SessionLocal() as session:
        analysis = await session.get(Analysis, UUID(analysis_id))
        if analysis is None or analysis.status != AnalysisStatus.queued:
            return
        analysis.status = AnalysisStatus.running
        await session.commit()
        analysis.status = AnalysisStatus.failed
        analysis.error_category = "model_not_deployed"
        analysis.completed_at = datetime.now(UTC)
        analysis.result = {
            "message": "No approved inference model is deployed.",
            "model_version": analysis.model_version,
        }
        await session.commit()


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
    functions = [run_inference, run_model_inference]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings: RedisSettings = redis_settings()
    queue_name = "inference"
