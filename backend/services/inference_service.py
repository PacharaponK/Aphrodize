from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import InferenceRequest
from backend.core.db.models import InferenceRun
from backend.libs.redis_client import get_arq_pool


async def create_inference_run(session: AsyncSession, payload: InferenceRequest) -> InferenceRun:
    run = InferenceRun(
        model_family=payload.model_family,
        model_uri=payload.model_uri,
        input_data=payload.input_data,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    redis = await get_arq_pool()
    await redis.enqueue_job("run_model_inference", str(run.id), _queue_name="inference")
    await redis.close()
    return run
