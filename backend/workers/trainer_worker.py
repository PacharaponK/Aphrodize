import asyncio
import logging
from datetime import UTC
from uuid import UUID

import mlflow
from arq import cron
from arq.connections import RedisSettings

from backend.core.config import settings
from backend.core.db.models import TrainingRun
from backend.core.db.session import SessionLocal, close_database
from backend.core.observability import observed_job, start_worker_metrics, stop_worker_metrics
from backend.libs.redis_client import redis_settings
from backend.services.curated_training import train_candidate
from backend.services.daily_health_tracking import track_daily_health_candidate
from backend.services.daily_health_training import (
    enqueue_candidate_training_if_ready,
    train_daily_health_candidate,
)

logger = logging.getLogger(__name__)


def _train_with_mlflow(run: TrainingRun) -> str:
    """Train one validated image candidate inside a traceable MLflow run."""
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    with mlflow.start_run(run_name=f"aphrodize-{run.model_family}") as mlflow_run:
        mlflow.log_params({"model_family": run.model_family, **run.config})
        mlflow.set_tag("dataset_uri", run.dataset_uri)
        train_candidate(run.dataset_uri, epochs=run.config.get("epochs", 1))
        return mlflow_run.info.run_id


async def shutdown(ctx: dict) -> None:
    await stop_worker_metrics(ctx)
    await close_database()


@observed_job
async def run_training(ctx: dict, training_run_id: str) -> None:
    """Train approved image datasets; keep other model families as placeholders."""
    async with SessionLocal() as session:
        # Fetch the request saved by training_service before it entered Redis.
        run = await session.get(TrainingRun, UUID(training_run_id))
        if run is None or run.status != "queued":
            ctx["telemetry_outcome"] = "skipped"
            return
        run.status = "running"
        await session.commit()
        try:
            if run.model_family == "image_segmentation":
                # Real image training runs off the async event loop.
                run.mlflow_run_id = await asyncio.to_thread(_train_with_mlflow, run)
                # Training success never deploys the candidate automatically.
                run.status = "awaiting_approval"
            else:
                # Other model families currently record metadata only.
                mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
                with mlflow.start_run(run_name=f"aphrodize-{run.model_family}") as mlflow_run:
                    mlflow.log_params({"model_family": run.model_family, **run.config})
                    mlflow.set_tag("dataset_uri", run.dataset_uri)
                    mlflow.set_tag("execution_kind", "metadata_only")
                    mlflow.set_tag("training_executed", "false")
                    run.mlflow_run_id = mlflow_run.info.run_id
                    run.status = "awaiting_model_package"
        except Exception:
            # Keep internal error details in logs and expose a failed status.
            logger.exception("Training run %s failed", training_run_id)
            run.status = "failed"
            ctx["telemetry_outcome"] = "failed"
        await session.commit()


@observed_job
async def run_daily_health_candidate_training(_: dict) -> None:
    """Create a review-only version when enough consented self-reports have arrived."""
    async with SessionLocal() as session:
        version = await train_daily_health_candidate(session)
        if version is not None and version.status == "candidate" and not version.mlflow_run_id:
            # Keep MLflow I/O outside the worker event loop. A tracking outage must
            # not discard an already-persisted candidate or activate it.
            try:
                version.mlflow_run_id = await asyncio.to_thread(
                    track_daily_health_candidate, version
                )
                await session.commit()
            except Exception as error:
                logger.warning("Candidate tracking unavailable: %s", type(error).__name__)
                raise


@observed_job
async def check_daily_health_candidate_training(_: dict) -> None:
    """Weekly: queue a candidate run only if the consented cohort passes readiness checks."""
    async with SessionLocal() as session:
        await enqueue_candidate_training_if_ready(session)


class WorkerSettings:
    functions = [run_training, run_daily_health_candidate_training]
    # Monday 02:00 UTC is Monday 09:00 in the tracker’s Asia/Bangkok timezone.
    timezone = UTC
    cron_jobs = [
        cron(
            check_daily_health_candidate_training,
            weekday="mon",
            hour=2,
            minute=0,
            run_at_startup=False,
        )
    ]
    on_shutdown = shutdown
    on_startup = start_worker_metrics
    health_check_interval = 30
    redis_settings: RedisSettings = redis_settings()
    queue_name = "training"
