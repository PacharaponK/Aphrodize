from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import TrainingRequest
from backend.core.db.models import TrainingRun
from backend.libs.redis_client import get_arq_pool


async def create_training_run(session: AsyncSession, payload: TrainingRequest) -> TrainingRun:
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
