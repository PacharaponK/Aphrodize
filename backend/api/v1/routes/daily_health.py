from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.api.schemas.daily_health import (
    DailyHealthEntryRead,
    DailyHealthEntryUpsert,
    DailyHealthOutcomeRead,
    DailyHealthOutcomeUpsert,
    DailyHealthPredictionRequest,
)
from backend.core.db.models import (
    Consent,
    DailyHealthAgeBand,
    DailyHealthEntry,
    DailyHealthMenstrualCheckIn,
    DailyHealthOutcome,
    DailyHealthProfile,
    User,
)
from backend.core.db.session import get_session
from backend.libs.model_loader import get_daily_score_model

router = APIRouter()
SLEEP_SCORE_METHOD = "min(100, sleep_duration_minutes / 420 * 100); duration-only"
DAILY_HEALTH_CONSENT_VERSION = "daily-health-v1"
PERSONALIZATION_CONSENT_VERSION = "daily-health-personalization-v1"
AGE_GUIDANCE_CONSENT_VERSION = "daily-health-age-guidance-v1"


@router.post("/predict")
def predict_daily_health(payload: DailyHealthPredictionRequest) -> dict:
    return _run_daily_health_prediction(payload, allow_out_of_domain_test_prediction=False)


@router.post("/predict/test")
def predict_daily_health_test(payload: DailyHealthPredictionRequest) -> dict:
    """Return explicitly experimental scores outside the train domain for test-only evaluation."""
    return _run_daily_health_prediction(payload, allow_out_of_domain_test_prediction=True)


def _run_daily_health_prediction(
    payload: DailyHealthPredictionRequest,
    *,
    allow_out_of_domain_test_prediction: bool,
) -> dict:
    try:
        model = get_daily_score_model()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Daily score model is unavailable") from error

    try:
        personal_context = payload.personal_context
        return model.predict_daily_health(
            local_date=payload.local_date,
            sleep_hours=payload.sleep_hours,
            sleep_minutes=payload.sleep_minutes,
            water_intake_ml=payload.water_intake_ml,
            outdoor_exposure_choice=payload.outdoor_exposure_choice,
            smoking_status=(
                personal_context.smoking_status
                if personal_context and personal_context.consent_given
                else None
            ),
            currently_menstruating=(
                personal_context.currently_menstruating
                if personal_context and personal_context.consent_given
                else None
            ),
            age_band=(
                personal_context.age_band
                if personal_context and personal_context.age_guidance_consent_given
                else None
            ),
            allow_out_of_domain_test_prediction=allow_out_of_domain_test_prediction,
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

    if payload.personalization_consent or payload.age_guidance_consent:
        if payload.personalization_consent:
            active_profile_consent = await session.scalar(
                select(Consent.id)
                .where(
                    Consent.user_id == user_id,
                    Consent.version == PERSONALIZATION_CONSENT_VERSION,
                    Consent.revoked_at.is_(None),
                )
                .limit(1)
            )
            if active_profile_consent is None:
                session.add(Consent(user_id=user_id, version=PERSONALIZATION_CONSENT_VERSION))

        if payload.age_guidance_consent:
            active_age_consent = await session.scalar(
                select(Consent.id)
                .where(
                    Consent.user_id == user_id,
                    Consent.version == AGE_GUIDANCE_CONSENT_VERSION,
                    Consent.revoked_at.is_(None),
                )
                .limit(1)
            )
            if active_age_consent is None:
                session.add(Consent(user_id=user_id, version=AGE_GUIDANCE_CONSENT_VERSION))

        if payload.personalization_consent and payload.smoking_status is not None:
            profile_upsert = insert(DailyHealthProfile).values(
                user_id=user_id,
                smoking_status=payload.smoking_status,
                updated_at=func.now(),
            )
            profile_upsert = profile_upsert.on_conflict_do_update(
                index_elements=[DailyHealthProfile.user_id],
                set_={
                    "smoking_status": profile_upsert.excluded.smoking_status,
                    "updated_at": func.now(),
                },
            )
            await session.execute(profile_upsert)

        if payload.age_guidance_consent and payload.age_band is not None:
            age_upsert = insert(DailyHealthAgeBand).values(
                user_id=user_id,
                age_band=payload.age_band,
                updated_at=func.now(),
            )
            age_upsert = age_upsert.on_conflict_do_update(
                index_elements=[DailyHealthAgeBand.user_id],
                set_={
                    "age_band": age_upsert.excluded.age_band,
                    "updated_at": func.now(),
                },
            )
            await session.execute(age_upsert)

        if payload.personalization_consent and payload.currently_menstruating is not None:
            checkin_upsert = insert(DailyHealthMenstrualCheckIn).values(
                user_id=user_id,
                local_date=payload.local_date,
                currently_menstruating=payload.currently_menstruating,
            )
            checkin_upsert = checkin_upsert.on_conflict_do_update(
                index_elements=[
                    DailyHealthMenstrualCheckIn.user_id,
                    DailyHealthMenstrualCheckIn.local_date,
                ],
                set_={"currently_menstruating": checkin_upsert.excluded.currently_menstruating},
            )
            await session.execute(checkin_upsert)

    await session.commit()
    return DailyHealthEntryRead.model_validate(entry)


@router.get("/users/{user_id}/profile")
async def read_daily_health_profile(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    active_daily_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == DAILY_HEALTH_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    active_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == PERSONALIZATION_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    active_age_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == AGE_GUIDANCE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    profile = await session.get(DailyHealthProfile, user_id)
    age_band = await session.get(DailyHealthAgeBand, user_id)
    return {
        "consent_active": active_consent is not None,
        "age_guidance_consent_active": active_age_consent is not None,
        "can_report_outcomes": active_daily_consent is not None,
        "age_band": (
            age_band.age_band if active_age_consent is not None and age_band else None
        ),
        "smoking_status": (
            profile.smoking_status if active_consent is not None and profile else None
        ),
    }


@router.delete("/users/{user_id}/profile", status_code=204)
async def delete_daily_health_profile(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    await session.execute(
        delete(DailyHealthProfile).where(DailyHealthProfile.user_id == user_id)
    )
    await session.execute(
        delete(DailyHealthAgeBand).where(DailyHealthAgeBand.user_id == user_id)
    )
    await session.execute(
        delete(DailyHealthMenstrualCheckIn).where(
            DailyHealthMenstrualCheckIn.user_id == user_id
        )
    )
    await session.execute(
        Consent.__table__.update()
        .where(
            Consent.user_id == user_id,
            Consent.version.in_([PERSONALIZATION_CONSENT_VERSION, AGE_GUIDANCE_CONSENT_VERSION]),
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await session.commit()


@router.put("/users/{user_id}/outcomes", response_model=DailyHealthOutcomeRead)
async def upsert_daily_health_outcome(
    user_id: UUID,
    payload: DailyHealthOutcomeUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthOutcomeRead:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    bangkok_time = datetime.now(UTC).astimezone(timezone(timedelta(hours=7)))
    if payload.target_date > bangkok_time.date():
        raise HTTPException(status_code=422, detail="Outcome date cannot be in the future")

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

    statement = insert(DailyHealthOutcome).values(
        user_id=user_id,
        target_date=payload.target_date,
        reported_energy_level_0_10=payload.reported_energy_level_0_10,
        reported_thirst_level_0_10=payload.reported_thirst_level_0_10,
        updated_at=func.now(),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthOutcome.user_id, DailyHealthOutcome.target_date],
        set_={
            "reported_energy_level_0_10": statement.excluded.reported_energy_level_0_10,
            "reported_thirst_level_0_10": statement.excluded.reported_thirst_level_0_10,
            "updated_at": func.now(),
        },
    ).returning(DailyHealthOutcome)

    result = await session.execute(statement)
    outcome = result.scalar_one()
    await session.commit()
    return DailyHealthOutcomeRead.model_validate(outcome)
