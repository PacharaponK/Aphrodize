from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import TrainingRequest
from backend.core.db.models import TrainingRun
from backend.core.observability import enqueue_job
from backend.libs.redis_client import get_arq_pool
from backend.services.curated_training import DATASET_URI


async def create_training_run(session: AsyncSession, payload: TrainingRequest) -> TrainingRun:
    # Image training accepts only a referenced approved dataset and bounded epoch count.
    if payload.model_family == "image_segmentation":
        # Default to one epoch and reject every unsupported training option.
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
    # Save the request before enqueueing so the trainer can fetch it by ID.
    run = TrainingRun(
        model_family=payload.model_family,
        dataset_uri=payload.dataset_uri,
        config=payload.config,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    # Training has its own queue and does not block image inference.
    redis = await get_arq_pool()
    await enqueue_job(redis, "run_training", str(run.id), _queue_name="training")
    await redis.close()
    return run
