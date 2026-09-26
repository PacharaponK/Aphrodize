from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.forecast import (
    LifestyleForecastRead,
    LifestyleObservationCreate,
    LifestyleObservationRead,
)
from backend.core.db.models import DailyLifestyleObservation, User
from backend.core.db.session import get_session
from backend.libs.model_loader import get_lifestyle_forecast_model

router = APIRouter()
forecast_model = get_lifestyle_forecast_model()


@router.post(
    "/users/{user_id}/observations",
    response_model=LifestyleObservationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_observation(
    user_id: UUID,
    payload: LifestyleObservationCreate,
    session: AsyncSession = Depends(get_session),
) -> LifestyleObservationRead:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    observation = DailyLifestyleObservation(user_id=user_id, **payload.model_dump())
    session.add(observation)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="An observation already exists for this date."
        ) from exc
    await session.refresh(observation)
    return LifestyleObservationRead(id=str(observation.id), **payload.model_dump())


@router.get("/users/{user_id}", response_model=LifestyleForecastRead)
async def get_forecast(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> LifestyleForecastRead:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    observations = list(
        (
            await session.scalars(
                select(DailyLifestyleObservation)
                .where(DailyLifestyleObservation.user_id == user_id)
                .order_by(DailyLifestyleObservation.date)
            )
        ).all()
    )
    report = forecast_model.build_report(
        [
            forecast_model.DailyObservation(
                observed_on=item.date,
                wrinkle_score=item.wrinkle_score,
                sleep_hours=item.sleep_hours,
                water_intake_ml=item.water_intake_ml,
                outdoor_minutes=item.outdoor_minutes,
            )
            for item in observations
        ]
    )
    return LifestyleForecastRead(user_id=str(user_id), report=report)
