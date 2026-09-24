from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import InferenceRequest, InferenceRunRead
from backend.core.db.models import InferenceRun
from backend.core.db.session import get_session
from backend.services.inference_service import create_inference_run

router = APIRouter()


def serialize(run: InferenceRun) -> InferenceRunRead:
    return InferenceRunRead(
        id=run.id,
        model_family=run.model_family,
        model_uri=run.model_uri,
        status=run.status,
        result=run.result,
        error_category=run.error_category,
        created_at=run.created_at,
    )


@router.post("/runs", response_model=InferenceRunRead, status_code=status.HTTP_202_ACCEPTED)
async def submit_inference(
    payload: InferenceRequest, session: AsyncSession = Depends(get_session)
) -> InferenceRunRead:
    return serialize(await create_inference_run(session, payload))


@router.get("/runs/{run_id}", response_model=InferenceRunRead)
async def get_inference(
    run_id: UUID, session: AsyncSession = Depends(get_session)
) -> InferenceRunRead:
    run = await session.get(InferenceRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Inference run not found")
    return serialize(run)
