import asyncio
import logging
from uuid import UUID

import mlflow
from arq.connections import RedisSettings

from backend.core.config import settings
from backend.core.db.models import TrainingRun
from backend.core.db.session import SessionLocal, close_database
from backend.libs.redis_client import redis_settings
from backend.services.daily_health_training import train_daily_health_candidate


async def shutdown(_: dict) -> None:
    await close_database()


async def run_training(_: dict, training_run_id: str) -> None:
    """Train approved image datasets; keep other model families as placeholders."""
    async with SessionLocal() as session:
        # Fetch the request saved by training_service before it entered Redis.
        run = await session.get(TrainingRun, UUID(training_run_id))
        if run is None or run.status != "queued":
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
                    run.mlflow_run_id = mlflow_run.info.run_id
                    run.status = "awaiting_model_package"
        except Exception:
            # Keep internal error details in logs and expose a failed status.
            logger.exception("Training run %s failed", training_run_id)
            run.status = "failed"
        await session.commit()


async def run_daily_health_candidate_training(_: dict) -> None:
    """Create a review-only version when enough consented self-reports have arrived."""
    async with SessionLocal() as session:
        await train_daily_health_candidate(session)


class WorkerSettings:
    functions = [run_training, run_daily_health_candidate_training]
    on_shutdown = shutdown
    redis_settings: RedisSettings = redis_settings()
    queue_name = "training"
