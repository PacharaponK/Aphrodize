from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import TrainingRequest, TrainingRunRead
from backend.core.db.models import TrainingRun
from backend.core.db.session import get_session
from backend.services.training_service import create_training_run

router = APIRouter()


def serialize(run: TrainingRun) -> TrainingRunRead:
    return TrainingRunRead(
        id=run.id,
        model_family=run.model_family,
        dataset_uri=run.dataset_uri,
        status=run.status,
        mlflow_run_id=run.mlflow_run_id,
        created_at=run.created_at,
        execution_kind=(
            "model_training" if run.model_family == "image_segmentation" else "metadata_only"
        ),
    )


# Training requests enqueue work; the returned run ID is used to poll its outcome.
@router.post("/runs", response_model=TrainingRunRead, status_code=status.HTTP_202_ACCEPTED)
async def submit_training(
    payload: TrainingRequest, session: AsyncSession = Depends(get_session)
) -> TrainingRunRead:
    # The service validates the request, stores it, and enqueues the worker job.
    run = await create_training_run(session, payload)
    return serialize(run)


@router.get("/runs/{run_id}", response_model=TrainingRunRead)
async def get_training_run(
    run_id: UUID, session: AsyncSession = Depends(get_session)
) -> TrainingRunRead:
    # Poll this endpoint for queued, running, failed, or approval-pending status.
    run = await session.get(TrainingRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Training run not found")
    return serialize(run)
