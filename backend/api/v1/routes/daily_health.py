from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.api.schemas.daily_health import (
    DailyHealthEntryRead,
    DailyHealthEntryUpsert,
    DailyHealthAgeBandRead,
    DailyHealthAgeBandUpsert,
    DailyHealthMenstrualCheckinRead,
    DailyHealthMenstrualCheckinUpsert,
    DailyHealthOutcomeRead,
    DailyHealthOutcomeUpsert,
    DailyHealthPredictionRequest,
    DailyHealthProfileRead,
    DailyHealthProfileUpsert,
)
from backend.core.db.models import (
    Consent,
    DailyHealthAgeBand,
    DailyHealthEntry,
    DailyHealthMenstrualCheckin,
    DailyHealthOutcome,
    DailyHealthProfile,
    User,
)
from backend.core.db.session import get_session
from backend.libs.model_loader import get_daily_score_model

router = APIRouter()
SLEEP_SCORE_METHOD = "min(100, sleep_duration_minutes / 420 * 100); duration-only"
DAILY_HEALTH_CONSENT_VERSION = "daily-health-v1"
DAILY_HEALTH_AGE_GUIDANCE_CONSENT_VERSION = "daily-health-age-guidance-v1"
DAILY_HEALTH_PERSONALIZATION_CONSENT_VERSION = "daily-health-personalization-v1"


async def require_active_consent(
    session: AsyncSession, user_id: UUID, version: str = DAILY_HEALTH_CONSENT_VERSION
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    active_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == version,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_consent is None:
        raise HTTPException(status_code=403, detail=f"Active {version} consent is required")


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
    await require_active_consent(session, user_id)

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
        "prediction_target_date": payload.local_date + timedelta(days=1) if prediction else None,
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


@router.get("/users/{user_id}/entries")
async def list_daily_health_entries(
    user_id: UUID,
    limit: int = Query(default=30, ge=1, le=90),
    from_date: date | None = None,
    to_date: date | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the signed-in user's saved tracker history while consent is active."""
    if (from_date is None) != (to_date is None):
        raise HTTPException(
            status_code=422, detail="Both from_date and to_date are required together"
        )
    if from_date is not None and to_date is not None:
        if from_date > to_date:
            raise HTTPException(status_code=422, detail="from_date must not be after to_date")
        if (to_date - from_date).days >= 90:
            raise HTTPException(status_code=422, detail="Date window cannot exceed 90 days")

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
        return {"items": []}

    statement = select(DailyHealthEntry).where(DailyHealthEntry.user_id == user_id)
    if from_date is not None and to_date is not None:
        statement = statement.where(
            DailyHealthEntry.local_date >= from_date,
            DailyHealthEntry.local_date <= to_date,
        )
    result = await session.scalars(
        statement.order_by(DailyHealthEntry.local_date.desc()).limit(limit)
    )
    entries = result.all()
    if not entries:
        return {"items": []}
    try:
        model = get_daily_score_model()
    except RuntimeError as error:
        raise HTTPException(
            status_code=503, detail="Daily health history is unavailable"
        ) from error

    # This version stores prediction scores but not a separately reviewed risk
    # interpretation. Mark those cards unavailable instead of manufacturing one.
    unavailable = {
        "level": None,
        "status": "not_available",
        "headline": "ยังไม่มีผลประเมินความเสี่ยงสำหรับบันทึกนี้",
    }

    def history_item(entry: DailyHealthEntry) -> dict:
        in_training_domain = (
            model.SLEEP_RANGE[0] <= entry.sleep_duration_minutes <= model.SLEEP_RANGE[1]
            and model.WATER_RANGE[0] <= entry.water_intake_ml <= model.WATER_RANGE[1]
        )
        prediction_available = entry.prediction_status == "predicted" and in_training_domain
        thirst_score = entry.predicted_thirst_score_0_10 if prediction_available else None
        dryness_score = entry.predicted_dryness_score_0_10 if prediction_available else None
        return {
            "local_date": entry.local_date.isoformat(),
            "prediction_target_date": (
                entry.prediction_target_date.isoformat()
                if entry.prediction_target_date is not None
                else None
            ),
            "prediction_status": entry.prediction_status,
            "prediction_model_id": entry.prediction_model_id,
            "input_domain_status": (
                "in_domain" if in_training_domain else "out_of_training_domain"
            ),
            "input": {
                "sleep_duration_total_minutes": entry.sleep_duration_minutes,
                "water_intake_ml": entry.water_intake_ml,
                "outdoor_exposure_choice": entry.outdoor_exposure_choice,
            },
            "calculated": {"sleep_score_0_100": entry.sleep_score_0_100},
            "predictions": {
                "thirst_score_0_10": {
                    "value": thirst_score,
                    "status": "predicted" if thirst_score is not None else "not_available",
                    "target_date": (
                        entry.prediction_target_date.isoformat()
                        if entry.prediction_target_date is not None
                        else None
                    ),
                },
                "skin_dryness_score_0_10": {
                    "value": dryness_score,
                    "status": "predicted" if dryness_score is not None else "not_available",
                    "target_date": (
                        entry.prediction_target_date.isoformat()
                        if entry.prediction_target_date is not None
                        else None
                    ),
                },
            },
            "interpretation": {
                "daily_health_summary": unavailable,
                "skin_care_attention_level": unavailable,
                "acne_flare_signal": unavailable,
                "next_day_predictions": {
                    "low_energy_signal": unavailable,
                    "thirst_attention": unavailable,
                },
                "profile_guidance": [],
            },
        }

    return {"items": [history_item(entry) for entry in entries]}


@router.put("/users/{user_id}/profile", response_model=DailyHealthProfileRead)
async def upsert_daily_health_profile(
    user_id: UUID,
    payload: DailyHealthProfileUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthProfileRead:
    await require_active_consent(session, user_id)
    statement = insert(DailyHealthProfile).values(user_id=user_id, **payload.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthProfile.user_id],
        set_={"smoking_status": statement.excluded.smoking_status, "updated_at": func.now()},
    ).returning(DailyHealthProfile)
    profile = (await session.execute(statement)).scalar_one()
    await session.commit()
    return DailyHealthProfileRead.model_validate(profile)


@router.put("/users/{user_id}/age-band", response_model=DailyHealthAgeBandRead)
async def upsert_daily_health_age_band(
    user_id: UUID,
    payload: DailyHealthAgeBandUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthAgeBandRead:
    await require_active_consent(session, user_id, DAILY_HEALTH_AGE_GUIDANCE_CONSENT_VERSION)
    statement = insert(DailyHealthAgeBand).values(user_id=user_id, **payload.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthAgeBand.user_id],
        set_={"age_band": statement.excluded.age_band, "updated_at": func.now()},
    ).returning(DailyHealthAgeBand)
    age_band = (await session.execute(statement)).scalar_one()
    await session.commit()
    return DailyHealthAgeBandRead.model_validate(age_band)


@router.put("/users/{user_id}/menstrual-checkins", response_model=DailyHealthMenstrualCheckinRead)
async def upsert_menstrual_checkin(
    user_id: UUID,
    payload: DailyHealthMenstrualCheckinUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthMenstrualCheckinRead:
    await require_active_consent(session, user_id, DAILY_HEALTH_PERSONALIZATION_CONSENT_VERSION)
    statement = insert(DailyHealthMenstrualCheckin).values(user_id=user_id, **payload.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthMenstrualCheckin.user_id, DailyHealthMenstrualCheckin.local_date],
        set_={"currently_menstruating": statement.excluded.currently_menstruating},
    ).returning(DailyHealthMenstrualCheckin)
    checkin = (await session.execute(statement)).scalar_one()
    await session.commit()
    return DailyHealthMenstrualCheckinRead.model_validate(checkin)


@router.put("/users/{user_id}/outcomes", response_model=DailyHealthOutcomeRead)
async def upsert_daily_health_outcome(
    user_id: UUID,
    payload: DailyHealthOutcomeUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthOutcomeRead:
    await require_active_consent(session, user_id)
    statement = insert(DailyHealthOutcome).values(user_id=user_id, **payload.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthOutcome.user_id, DailyHealthOutcome.target_date],
        set_={
            "reported_energy_level_0_10": statement.excluded.reported_energy_level_0_10,
            "reported_thirst_level_0_10": statement.excluded.reported_thirst_level_0_10,
            "reported_dryness_level_0_10": statement.excluded.reported_dryness_level_0_10,
            "updated_at": func.now(),
        },
    ).returning(DailyHealthOutcome)
    outcome = (await session.execute(statement)).scalar_one()
    await session.commit()
    return DailyHealthOutcomeRead.model_validate(outcome)
