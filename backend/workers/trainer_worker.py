from uuid import UUID

import mlflow
from arq.connections import RedisSettings

from backend.core.config import settings
from backend.core.db.models import TrainingRun
from backend.core.db.session import SessionLocal, close_database
from backend.libs.redis_client import redis_settings


async def shutdown(_: dict) -> None:
    await close_database()


async def run_training(_: dict, training_run_id: str) -> None:
    """Create a reproducible MLflow run; training code belongs in a reviewed model package."""
    async with SessionLocal() as session:
        run = await session.get(TrainingRun, UUID(training_run_id))
        if run is None or run.status != "queued":
            return
        run.status = "running"
        await session.commit()
        try:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            with mlflow.start_run(run_name=f"aphrodize-{run.model_family}") as mlflow_run:
                mlflow.log_params({"model_family": run.model_family, **run.config})
                mlflow.set_tag("dataset_uri", run.dataset_uri)
                mlflow.set_tag("training_data_policy", "no user inference images")
                run.mlflow_run_id = mlflow_run.info.run_id
                run.status = "awaiting_model_package"
        except Exception:
            run.status = "failed"
        await session.commit()


class WorkerSettings:
    functions = [run_training]
    on_shutdown = shutdown
    redis_settings: RedisSettings = redis_settings()
    queue_name = "training"
