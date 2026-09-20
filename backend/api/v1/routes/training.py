from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import TrainingRequest, TrainingRunRead
from backend.core.db.session import get_session
from backend.services.training_service import create_training_run

router = APIRouter()


@router.post("/runs", response_model=TrainingRunRead, status_code=status.HTTP_202_ACCEPTED)
async def submit_training(
    payload: TrainingRequest, session: AsyncSession = Depends(get_session)
) -> TrainingRunRead:
    run = await create_training_run(session, payload)
    return TrainingRunRead(
        id=run.id,
        model_family=run.model_family,
        dataset_uri=run.dataset_uri,
        status=run.status,
        mlflow_run_id=run.mlflow_run_id,
        created_at=run.created_at,
    )
