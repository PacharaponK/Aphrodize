from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import TrainingRequest
from backend.core.db.models import TrainingRun
from backend.libs.redis_client import get_arq_pool
from backend.services.curated_training import DATASET_URI


async def create_training_run(session: AsyncSession, payload: TrainingRequest) -> TrainingRun:
    if payload.model_family == "image_segmentation":
        epochs = payload.config.get("epochs", 1)
        if (
            not DATASET_URI.fullmatch(payload.dataset_uri)
            or type(epochs) is not int
            or not 1 <= epochs <= 20
            or set(payload.config) - {"epochs"}
        ):
            raise HTTPException(
                status_code=422,
                detail="Image training requires approved://<id>@<manifest_sha256> and 1-20 epochs",
            )
    run = TrainingRun(
        model_family=payload.model_family,
        dataset_uri=payload.dataset_uri,
        config=payload.config,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    redis = await get_arq_pool()
    await redis.enqueue_job("run_training", str(run.id), _queue_name="training")
    await redis.close()
    return run
