from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.api.schemas.daily_health import (
    DailyHealthEntryRead,
    DailyHealthEntryUpsert,
    DailyHealthPredictionRequest,
)
from backend.core.db.models import Consent, DailyHealthEntry, User
from backend.core.db.session import get_session
from backend.libs.model_loader import get_daily_score_model

router = APIRouter()
SLEEP_SCORE_METHOD = "min(100, sleep_duration_minutes / 420 * 100); duration-only"
DAILY_HEALTH_CONSENT_VERSION = "daily-health-v1"


@router.post("/predict")
def predict_daily_health(payload: DailyHealthPredictionRequest) -> dict:
    try:
        model = get_daily_score_model()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Daily score model is unavailable") from error

    try:
        return model.predict_daily_health(
            local_date=payload.local_date,
            sleep_hours=payload.sleep_hours,
            sleep_minutes=payload.sleep_minutes,
            water_intake_ml=payload.water_intake_ml,
            outdoor_exposure_choice=payload.outdoor_exposure_choice,
        )
    except model.ScoreModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail="Daily score model inference failed") from error


@router.put("/users/{user_id}/entries", response_model=DailyHealthEntryRead)
async def upsert_daily_health_entry(
    user_id: UUID,
    payload: DailyHealthEntryUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthEntryRead:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    active_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == DAILY_HEALTH_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_consent is None:
        raise HTTPException(status_code=403, detail="Active daily-health consent is required")

    sleep_score = round(min(100.0, payload.sleep_duration_minutes / 420.0 * 100.0), 1)
    prediction = payload.prediction
    values = {
        "user_id": user_id,
        "local_date": payload.local_date,
        "timezone": payload.timezone,
        "sleep_duration_minutes": payload.sleep_duration_minutes,
        "water_intake_ml": payload.water_intake_ml,
        "outdoor_exposure_choice": payload.outdoor_exposure_choice,
        "sleep_score_0_100": sleep_score,
        "sleep_score_method": SLEEP_SCORE_METHOD,
        "predicted_thirst_score_0_10": prediction.thirst_score_0_10 if prediction else None,
        "predicted_dryness_score_0_10": prediction.dryness_score_0_10 if prediction else None,
        "prediction_status": prediction.prediction_status if prediction else "not_run",
        "prediction_model_id": prediction.model_id if prediction else None,
        "data_source": "user_reported",
        "updated_at": func.now(),
    }
    statement = insert(DailyHealthEntry).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthEntry.user_id, DailyHealthEntry.local_date],
        set_={
            key: getattr(statement.excluded, key)
            for key in values
            if key not in {"user_id", "local_date", "data_source"}
        },
    ).returning(DailyHealthEntry)

    result = await session.execute(statement)
    entry = result.scalar_one()
    await session.commit()
    return DailyHealthEntryRead.model_validate(entry)
