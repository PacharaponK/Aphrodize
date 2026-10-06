import logging
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.api.deps import require_matching_user
from backend.api.schemas.daily_health import (
    DailyHealthAgeBandRead,
    DailyHealthAgeBandUpsert,
    DailyHealthEntryRead,
    DailyHealthEntryUpsert,
    DailyHealthMenstrualCheckinRead,
    DailyHealthMenstrualCheckinUpsert,
    DailyHealthModelPromotionRequest,
    DailyHealthModelRollbackRequest,
    DailyHealthOutcomeRead,
    DailyHealthOutcomeUpsert,
    DailyHealthPredictionRequest,
    DailyHealthProfileHeightUpsert,
    DailyHealthProfileRead,
    DailyHealthProfileUpsert,
    DailyHealthProfileWeightUpsert,
)
from backend.core.consents import MODEL_TRAINING_CONSENT_VERSION, MODEL_TRAINING_CONSENT_VERSIONS
from backend.core.db.models import (
    Consent,
    DailyHealthAgeBand,
    DailyHealthEntry,
    DailyHealthMenstrualCheckIn,
    DailyHealthModelDeployment,
    DailyHealthModelDeploymentEvent,
    DailyHealthModelVersion,
    DailyHealthOutcome,
    DailyHealthProfile,
    User,
)
from backend.core.db.session import get_session
from backend.libs.model_loader import get_daily_score_model
from backend.services.daily_health_forecast_receipt import (
    issue_forecast_receipt,
    verify_forecast_receipt,
)
from backend.services.daily_health_model_registry import (
    DailyHealthCandidateUnavailable,
    get_serving_daily_health_bundle,
    load_approved_candidate_bundle,
    purge_generated_candidate_artifacts,
)
from backend.services.daily_health_personal_forecast import (
    build_personal_daily_health_forecast,
)
from backend.services.daily_health_training import inputs_available_before_target

router = APIRouter()
user_router = APIRouter(dependencies=[Depends(require_matching_user)])
logger = logging.getLogger(__name__)
SLEEP_SCORE_METHOD = "round(min(100, sleep_duration_minutes / 540 * 100), 1); duration-only, 9h cap"
DAILY_HEALTH_CONSENT_VERSION = "daily-health-v1"
PERSONALIZATION_CONSENT_VERSION = "daily-health-personalization-v1"
PERSONAL_FORECAST_CONSENT_VERSION = "daily-health-personal-forecast-v1"
AGE_GUIDANCE_CONSENT_VERSION = "daily-health-age-guidance-v1"
SKIN_TYPE_GUIDANCE_CONSENT_VERSION = "daily-health-skin-type-guidance-v1"
WEIGHT_PROFILE_CONSENT_VERSION = "daily-health-weight-profile-v1"
HEIGHT_PROFILE_CONSENT_VERSION = "daily-health-height-profile-v1"


@router.post("/predict")
async def predict_daily_health(
    payload: DailyHealthPredictionRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await _run_daily_health_prediction(
        payload,
        session=session,
        allow_out_of_domain_test_prediction=False,
    )


@router.post("/predict/test")
async def predict_daily_health_test(
    payload: DailyHealthPredictionRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return explicitly experimental scores outside the train domain for test-only evaluation."""
    return await _run_daily_health_prediction(
        payload,
        session=session,
        allow_out_of_domain_test_prediction=True,
    )


async def _run_daily_health_prediction(
    payload: DailyHealthPredictionRequest,
    *,
    session: AsyncSession,
    allow_out_of_domain_test_prediction: bool,
) -> dict:
    try:
        model = get_daily_score_model()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Daily score model is unavailable") from error

    try:
        model_bundle = await get_serving_daily_health_bundle(session)
    except DailyHealthCandidateUnavailable as error:
        raise HTTPException(
            status_code=503, detail="Approved daily score model is unavailable"
        ) from error

    try:
        personal_context = payload.personal_context
        result = model.predict_daily_health(
            local_date=payload.local_date,
            sleep_hours=payload.sleep_hours,
            sleep_minutes=payload.sleep_minutes,
            water_intake_ml=payload.water_intake_ml,
            weight_kg=payload.weight_kg,
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
            skin_type=(
                personal_context.skin_type
                if personal_context and personal_context.skin_type_guidance_consent_given
                else None
            ),
            allow_out_of_domain_test_prediction=allow_out_of_domain_test_prediction,
            model_bundle=model_bundle,
        )
        result["forecast_receipt"] = issue_forecast_receipt(result)
        return result
    except model.ScoreModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail="Daily score model inference failed") from error


@user_router.put("/users/{user_id}/entries", response_model=DailyHealthEntryRead)
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

    sleep_score = round(min(100.0, payload.sleep_duration_minutes / 540.0 * 100.0), 1)
    prediction = payload.prediction
    next_day_forecasts = None
    if prediction is not None and prediction.forecast_receipt:
        try:
            next_day_forecasts = verify_forecast_receipt(
                prediction.forecast_receipt, local_date=payload.local_date,
                sleep_minutes=payload.sleep_duration_minutes, water_ml=payload.water_intake_ml,
                outdoors=payload.outdoor_exposure_choice,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail="Forecast receipt is invalid or expired",
            ) from error
    score_model = get_daily_score_model()
    active_weight_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == WEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    profile = await session.get(DailyHealthProfile, user_id)
    profile_weight_kg = (
        profile.weight_kg
        if active_weight_consent is not None and profile is not None
        else None
    )
    hydration = score_model.calculate_hydration(
        payload.water_intake_ml,
        profile_weight_kg,
        payload.age_band if payload.age_guidance_consent else None,
    )
    values = {
        "user_id": user_id,
        "local_date": payload.local_date,
        "timezone": payload.timezone,
        "sleep_duration_minutes": payload.sleep_duration_minutes,
        "water_intake_ml": payload.water_intake_ml,
        # Keep the consented profile weight as a dated snapshot; do not trust a daily-form value.
        "weight_kg": profile_weight_kg,
        "calculated_thirst_score_0_10": hydration["score_0_10"],
        "thirst_score_method": score_model.THIRST_SCORE_METHOD,
        "outdoor_exposure_choice": payload.outdoor_exposure_choice,
        "sleep_score_0_100": sleep_score,
        "sleep_score_method": SLEEP_SCORE_METHOD,
        "predicted_thirst_score_0_10": prediction.thirst_score_0_10 if prediction else None,
        "predicted_dryness_score_0_10": prediction.dryness_score_0_10 if prediction else None,
        "prediction_target_date": (
            prediction.target_date if prediction and prediction.target_date else payload.local_date
        )
        if prediction
        else None,
        "prediction_status": prediction.prediction_status if prediction else "not_run",
        "prediction_model_id": prediction.model_id if prediction else None,
        "next_day_forecasts": next_day_forecasts,
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

    if (
        payload.personalization_consent
        or payload.age_guidance_consent
        or payload.skin_type_guidance_consent
    ):
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

        if payload.skin_type_guidance_consent:
            active_skin_type_consent = await session.scalar(
                select(Consent.id)
                .where(
                    Consent.user_id == user_id,
                    Consent.version == SKIN_TYPE_GUIDANCE_CONSENT_VERSION,
                    Consent.revoked_at.is_(None),
                )
                .limit(1)
            )
            if active_skin_type_consent is None:
                session.add(Consent(user_id=user_id, version=SKIN_TYPE_GUIDANCE_CONSENT_VERSION))

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

        if payload.skin_type_guidance_consent and payload.skin_type is not None:
            skin_type_upsert = insert(DailyHealthProfile).values(
                user_id=user_id,
                skin_type=payload.skin_type,
                updated_at=func.now(),
            )
            skin_type_upsert = skin_type_upsert.on_conflict_do_update(
                index_elements=[DailyHealthProfile.user_id],
                set_={
                    "skin_type": skin_type_upsert.excluded.skin_type,
                    "updated_at": func.now(),
                },
            )
            await session.execute(skin_type_upsert)

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

    active_training_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == payload.model_training_consent_version,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if payload.model_training_consent and active_training_consent is None:
        session.add(Consent(user_id=user_id, version=payload.model_training_consent_version))

    await session.commit()
    response = DailyHealthEntryRead.model_validate(entry)
    if (
        (active_training_consent is not None or payload.model_training_consent)
        and entry.data_source == "user_reported"
        and inputs_available_before_target(entry, entry.local_date + timedelta(days=1))
    ):
        response.training_eligible = await session.scalar(
            select(DailyHealthOutcome.id)
            .where(
                DailyHealthOutcome.user_id == user_id,
                DailyHealthOutcome.target_date == entry.local_date + timedelta(days=1),
                DailyHealthOutcome.reported_thirst_level_0_10.is_not(None),
                DailyHealthOutcome.reported_dryness_level_0_10.is_not(None),
            )
            .limit(1)
        ) is not None
    return response


@user_router.get("/users/{user_id}/entries")
async def list_daily_health_entries(
    user_id: UUID,
    limit: int = Query(default=30, ge=1, le=90),
    from_date: date | None = None,
    to_date: date | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return consented daily history with risk interpretation of the saved scores."""
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

    active_daily_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == DAILY_HEALTH_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_daily_consent is None:
        return {"items": []}

    entries_query = select(DailyHealthEntry).where(DailyHealthEntry.user_id == user_id)
    if from_date is not None and to_date is not None:
        entries_query = entries_query.where(
            DailyHealthEntry.local_date >= from_date,
            DailyHealthEntry.local_date <= to_date,
        )
    entries_result = await session.scalars(
        entries_query.order_by(DailyHealthEntry.local_date.desc()).limit(limit)
    )
    entries = entries_result.all()
    if not entries:
        return {"items": []}

    active_personalization_consent = await session.scalar(
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
    active_skin_type_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == SKIN_TYPE_GUIDANCE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    profile = (
        await session.get(DailyHealthProfile, user_id)
        if active_personalization_consent is not None or active_skin_type_consent is not None
        else None
    )
    age_record = (
        await session.get(DailyHealthAgeBand, user_id) if active_age_consent is not None else None
    )
    menstrual_by_date: dict[date, bool] = {}
    if active_personalization_consent is not None:
        checkins_result = await session.scalars(
            select(DailyHealthMenstrualCheckIn).where(
                DailyHealthMenstrualCheckIn.user_id == user_id,
                DailyHealthMenstrualCheckIn.local_date.in_([entry.local_date for entry in entries]),
            )
        )
        menstrual_by_date = {
            checkin.local_date: checkin.currently_menstruating for checkin in checkins_result.all()
        }

    try:
        model = get_daily_score_model()
    except RuntimeError as error:
        raise HTTPException(
            status_code=503, detail="Daily health interpretation is unavailable"
        ) from error

    items = []
    for entry in entries:
        sleep_minutes = entry.sleep_duration_minutes
        inside_training_domain = (
            model.SLEEP_RANGE[0] <= sleep_minutes <= model.SLEEP_RANGE[1]
            and model.WATER_RANGE[0] <= entry.water_intake_ml <= model.WATER_RANGE[1]
        )
        input_domain_reasons = []
        if not model.SLEEP_RANGE[0] <= sleep_minutes <= model.SLEEP_RANGE[1]:
            input_domain_reasons.append("sleep_duration_outside_training_range")
        if not model.WATER_RANGE[0] <= entry.water_intake_ml <= model.WATER_RANGE[1]:
            input_domain_reasons.append("water_intake_outside_training_range")
        has_saved_prediction = (
            entry.prediction_status == "predicted"
            and entry.predicted_thirst_score_0_10 is not None
            and entry.predicted_dryness_score_0_10 is not None
        )
        thirst_is_calculated = entry.thirst_score_method == model.THIRST_SCORE_METHOD
        thirst_score = (
            entry.calculated_thirst_score_0_10
            if thirst_is_calculated
            else entry.predicted_thirst_score_0_10
            if has_saved_prediction
            else None
        )
        dryness_score = (
            entry.predicted_dryness_score_0_10 if entry.prediction_status == "predicted" else None
        )
        interpretation = model.build_health_interpretation(
            sleep_minutes=sleep_minutes,
            thirst_score=thirst_score,
            dryness_score=dryness_score,
            outdoor_exposure_choice=entry.outdoor_exposure_choice,
            input_domain_status="in_domain" if inside_training_domain else "out_of_training_domain",
            input_domain_reasons=input_domain_reasons,
            age_band=age_record.age_band if age_record is not None else None,
            smoking_status=(
                profile.smoking_status
                if active_personalization_consent is not None and profile is not None
                else None
            ),
            currently_menstruating=menstrual_by_date.get(entry.local_date),
            skin_type=(
                profile.skin_type
                if active_skin_type_consent is not None and profile is not None
                else None
            ),
            thirst_is_calculated=thirst_is_calculated,
        )
        items.append(
            {
                "local_date": entry.local_date.isoformat(),
                "prediction_target_date": (
                    entry.prediction_target_date.isoformat()
                    if entry.prediction_target_date is not None
                    else None
                ),
                "prediction_status": entry.prediction_status,
                "prediction_model_id": entry.prediction_model_id,
                "input_domain_status": (
                    "in_domain" if inside_training_domain else "out_of_training_domain"
                ),
                "input": {
                    "sleep_duration_total_minutes": sleep_minutes,
                    "water_intake_ml": entry.water_intake_ml,
                    "weight_kg": entry.weight_kg,
                    "outdoor_exposure_choice": entry.outdoor_exposure_choice,
                },
                "calculated": {
                    "sleep_score_0_100": entry.sleep_score_0_100,
                    "thirst_score_0_10": entry.calculated_thirst_score_0_10,
                    "thirst_score_method": entry.thirst_score_method,
                },
                "predictions": {
                    "thirst_score_0_10": {
                        "value": thirst_score,
                        "status": (
                            "calculated"
                            if thirst_is_calculated and thirst_score is not None
                            else "predicted"
                            if thirst_score is not None
                            else "not_available"
                        ),
                        "method": entry.thirst_score_method,
                        "target_date": entry.local_date.isoformat()
                        if thirst_is_calculated
                        else (
                            entry.prediction_target_date.isoformat()
                            if entry.prediction_target_date
                            else None
                        ),
                    },
                    "skin_dryness_score_0_10": {
                        "value": dryness_score,
                        "status": "predicted" if dryness_score is not None else "not_available",
                    },
                },
                "interpretation": {
                    **interpretation,
                    "next_day_predictions": {
                        **interpretation["next_day_predictions"],
                        **(entry.next_day_forecasts or {}),
                    },
                },
            }
        )

    return {"items": items}


@user_router.get("/users/{user_id}/personal-forecast")
async def get_personal_daily_health_forecast(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Forecast the next day's sleep and water values from this account's own diary."""
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
    if active_daily_consent is None:
        return {"enabled": False, "status": "daily_health_consent_required"}

    active_forecast_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == PERSONAL_FORECAST_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_forecast_consent is None:
        return {"enabled": False, "status": "consent_required"}

    today = _current_bangkok_date()
    history_start = today - timedelta(days=6)
    entries_result = await session.scalars(
        select(DailyHealthEntry)
        .where(
            DailyHealthEntry.user_id == user_id,
            DailyHealthEntry.data_source == "user_reported",
            DailyHealthEntry.local_date >= history_start,
            DailyHealthEntry.local_date <= today,
        )
        .order_by(DailyHealthEntry.local_date.asc())
    )
    forecast = build_personal_daily_health_forecast(
        entries_result.all(),
        user_id=user_id,
        as_of_date=today,
    )
    return {"enabled": True, **forecast}


@user_router.put("/users/{user_id}/personal-forecast-consent")
async def grant_personal_daily_health_forecast_consent(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await require_active_consent(session, user_id)
    active_forecast_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == PERSONAL_FORECAST_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_forecast_consent is None:
        session.add(Consent(user_id=user_id, version=PERSONAL_FORECAST_CONSENT_VERSION))
    await session.commit()
    return {"enabled": True, "scope": "account_only"}


@user_router.delete("/users/{user_id}/personal-forecast-consent", status_code=204)
async def revoke_personal_daily_health_forecast_consent(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == PERSONAL_FORECAST_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await session.commit()


def _current_bangkok_date() -> date:
    bangkok_timezone = timezone(timedelta(hours=7))
    return datetime.now(UTC).astimezone(bangkok_timezone).date()


@user_router.get("/users/{user_id}/profile")
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
    active_skin_type_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == SKIN_TYPE_GUIDANCE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    active_weight_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == WEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    active_height_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == HEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    active_training_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version.in_(MODEL_TRAINING_CONSENT_VERSIONS),
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    current_training_consent = await session.scalar(
        select(Consent.id).where(
            Consent.user_id == user_id, Consent.version == MODEL_TRAINING_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        ).limit(1)
    )
    profile = await session.get(DailyHealthProfile, user_id)
    age_band = await session.get(DailyHealthAgeBand, user_id)
    response = {
        "consent_active": active_consent is not None,
        "age_guidance_consent_active": active_age_consent is not None,
        "weight_profile_consent_active": active_weight_consent is not None,
        "weight_kg": (
            profile.weight_kg
            if active_weight_consent is not None and profile is not None
            else None
        ),
        "height_profile_consent_active": active_height_consent is not None,
        "height_cm": (
            profile.height_cm
            if active_height_consent is not None and profile is not None
            else None
        ),
        "model_training_consent_active": active_training_consent is not None,
        "model_training_consent_current_active": current_training_consent is not None,
        "can_report_outcomes": active_daily_consent is not None,
        "age_band": (age_band.age_band if active_age_consent is not None and age_band else None),
        "smoking_status": (
            profile.smoking_status if active_consent is not None and profile else None
        ),
    }
    if active_skin_type_consent is not None:
        response["skin_type_guidance_consent_active"] = True
        response["skin_type"] = profile.skin_type if profile is not None else None
    return response


@router.put("/users/{user_id}/profile/weight")
async def upsert_daily_health_profile_weight(
    user_id: UUID,
    payload: DailyHealthProfileWeightUpsert,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not payload.consent_given:
        raise HTTPException(status_code=403, detail="Weight profile consent is required")

    active_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == WEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_consent is None:
        session.add(Consent(user_id=user_id, version=WEIGHT_PROFILE_CONSENT_VERSION))

    profile_upsert = insert(DailyHealthProfile).values(
        user_id=user_id,
        weight_kg=payload.weight_kg,
        updated_at=func.now(),
    )
    profile_upsert = profile_upsert.on_conflict_do_update(
        index_elements=[DailyHealthProfile.user_id],
        set_={
            "weight_kg": profile_upsert.excluded.weight_kg,
            "updated_at": func.now(),
        },
    )
    await session.execute(profile_upsert)
    await session.commit()
    return {
        "weight_profile_consent_active": True,
        "weight_kg": payload.weight_kg,
    }


@router.put("/users/{user_id}/profile/height")
async def upsert_daily_health_profile_height(
    user_id: UUID,
    payload: DailyHealthProfileHeightUpsert,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not payload.consent_given:
        raise HTTPException(status_code=403, detail="Height profile consent is required")

    active_consent = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == HEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_consent is None:
        session.add(Consent(user_id=user_id, version=HEIGHT_PROFILE_CONSENT_VERSION))

    profile_upsert = insert(DailyHealthProfile).values(
        user_id=user_id,
        height_cm=payload.height_cm,
        updated_at=func.now(),
    )
    profile_upsert = profile_upsert.on_conflict_do_update(
        index_elements=[DailyHealthProfile.user_id],
        set_={
            "height_cm": profile_upsert.excluded.height_cm,
            "updated_at": func.now(),
        },
    )
    await session.execute(profile_upsert)
    await session.commit()
    return {"height_profile_consent_active": True, "height_cm": payload.height_cm}


@router.delete("/users/{user_id}/profile/height", status_code=204)
async def delete_daily_health_profile_height(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile = await session.get(DailyHealthProfile, user_id)
    if profile is not None:
        profile.height_cm = None
    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == HEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await session.commit()


@router.delete("/users/{user_id}/profile/weight", status_code=204)
async def delete_daily_health_profile_weight(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile = await session.get(DailyHealthProfile, user_id)
    if profile is not None:
        profile.weight_kg = None
    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == WEIGHT_PROFILE_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await session.execute(
        update(DailyHealthEntry)
        .where(DailyHealthEntry.user_id == user_id)
        .values(
            weight_kg=None,
            calculated_thirst_score_0_10=None,
            thirst_score_method=None,
            updated_at=func.now(),
        )
    )
    await session.commit()


@user_router.delete("/users/{user_id}/profile", status_code=204)
async def delete_daily_health_profile(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    await session.execute(delete(DailyHealthProfile).where(DailyHealthProfile.user_id == user_id))
    await session.execute(
        update(DailyHealthEntry)
        .where(DailyHealthEntry.user_id == user_id)
        .values(
            weight_kg=None,
            calculated_thirst_score_0_10=None,
            thirst_score_method=None,
            updated_at=func.now(),
        )
    )
    await session.execute(delete(DailyHealthAgeBand).where(DailyHealthAgeBand.user_id == user_id))
    await session.execute(
        delete(DailyHealthMenstrualCheckIn).where(DailyHealthMenstrualCheckIn.user_id == user_id)
    )
    await session.execute(
        Consent.__table__.update()
        .where(
            Consent.user_id == user_id,
            Consent.version.in_(
                [
                    PERSONALIZATION_CONSENT_VERSION,
                    AGE_GUIDANCE_CONSENT_VERSION,
                    SKIN_TYPE_GUIDANCE_CONSENT_VERSION,
                    WEIGHT_PROFILE_CONSENT_VERSION,
                    HEIGHT_PROFILE_CONSENT_VERSION,
                ]
            ),
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await session.commit()


@user_router.delete("/users/{user_id}/data", status_code=204)
async def delete_daily_health_data(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    """Erase this account's daily tracker data and invalidate shared user-trained candidates."""
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    had_training_consent = await session.scalar(
        select(Consent.id).where(
            Consent.user_id == user_id,
            Consent.version.in_(MODEL_TRAINING_CONSENT_VERSIONS),
        ).limit(1)
    )
    had_reported_entry = await session.scalar(
        select(DailyHealthEntry.id).where(
            DailyHealthEntry.user_id == user_id,
            DailyHealthEntry.data_source == "user_reported",
        ).limit(1)
    )
    had_reported_outcome = await session.scalar(
        select(DailyHealthOutcome.id).where(
            DailyHealthOutcome.user_id == user_id,
            DailyHealthOutcome.reported_thirst_level_0_10.is_not(None),
            DailyHealthOutcome.reported_dryness_level_0_10.is_not(None),
        ).limit(1)
    )
    may_have_trained_model = bool(
        had_training_consent and had_reported_entry and had_reported_outcome
    )
    model_version_ids = []
    deployment = None
    if may_have_trained_model:
        versions_result = await session.scalars(select(DailyHealthModelVersion))
        model_version_ids = [version.version_id for version in versions_result.all()]
        deployment = await session.get(DailyHealthModelDeployment, "daily_health")

    for record_model in (
        DailyHealthOutcome,
        DailyHealthEntry,
        DailyHealthMenstrualCheckIn,
        DailyHealthAgeBand,
        DailyHealthProfile,
    ):
        await session.execute(delete(record_model).where(record_model.user_id == user_id))

    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version.in_(
                [
                    DAILY_HEALTH_CONSENT_VERSION,
                    PERSONALIZATION_CONSENT_VERSION,
                    AGE_GUIDANCE_CONSENT_VERSION,
                    SKIN_TYPE_GUIDANCE_CONSENT_VERSION,
                    WEIGHT_PROFILE_CONSENT_VERSION,
                    HEIGHT_PROFILE_CONSENT_VERSION,
                    *MODEL_TRAINING_CONSENT_VERSIONS,
                ]
            ),
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    if may_have_trained_model:
        if deployment is not None:
            deployment.active_version_id = None
            deployment.previous_version_id = None
            deployment.approval_reason = None

        # Without per-version participant lineage, a possible contributor's erasure must
        # invalidate the shared user-trained registry; non-contributors cannot reset it.
        await session.execute(delete(DailyHealthModelDeploymentEvent))
        await session.execute(delete(DailyHealthModelVersion))
        session.add(
            DailyHealthModelDeploymentEvent(
                action="data_erasure",
                version_id=None,
                reason="User-requested erasure removed the user-trained model registry",
            )
        )
    await session.commit()

    if not may_have_trained_model:
        return
    try:
        # Model versions do not currently retain per-user cohort membership, so the only safe
        # erasure is to remove every generated user-candidate artifact and return to the baseline.
        from backend.services.daily_health_model_registry import VERSION_ID_PATTERN

        purge_generated_candidate_artifacts(
            [
                version_id
                for version_id in model_version_ids
                if VERSION_ID_PATTERN.fullmatch(version_id)
            ]
        )
    except DailyHealthCandidateUnavailable as error:
        logger.exception(
            "Daily-health rows were erased but a generated model artifact needs cleanup"
        )
        raise HTTPException(
            status_code=503,
            detail="Data was erased; generated model artifacts need operator review",
        ) from error


@router.get("/model-versions")
async def list_daily_health_model_versions(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    versions_result = await session.scalars(
        select(DailyHealthModelVersion)
        .order_by(DailyHealthModelVersion.created_at.desc())
        .limit(limit)
    )
    versions = versions_result.all()
    return {
        "items": [
            {
                "version_id": item.version_id,
                "model_family": item.model_family,
                "status": item.status,
                "training_records": item.training_records,
                "participant_count": item.participant_count,
                "metrics": item.metrics,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            }
            for item in versions
        ]
    }


@router.get("/model-deployment")
async def read_daily_health_model_deployment(
    session: AsyncSession = Depends(get_session),
) -> dict:
    deployment = await session.get(DailyHealthModelDeployment, "daily_health")
    if deployment is None:
        return {"active_version_id": None, "previous_version_id": None}
    return {
        "active_version_id": deployment.active_version_id,
        "previous_version_id": deployment.previous_version_id,
        "approval_reason": deployment.approval_reason,
        "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
    }


@router.get("/model-deployment/events")
async def list_daily_health_model_deployment_events(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    events_result = await session.scalars(
        select(DailyHealthModelDeploymentEvent)
        .order_by(DailyHealthModelDeploymentEvent.created_at.desc())
        .limit(limit)
    )
    return {
        "items": [
            {
                "action": event.action,
                "version_id": event.version_id,
                "reason": event.reason,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events_result.all()
        ]
    }


@router.put("/model-deployment")
async def promote_daily_health_model(
    payload: DailyHealthModelPromotionRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    version = await session.get(DailyHealthModelVersion, payload.version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Candidate model version not found")
    if version.status != "candidate":
        raise HTTPException(status_code=409, detail="Only candidate models can be approved")
    try:
        load_approved_candidate_bundle(version)
    except DailyHealthCandidateUnavailable as error:
        raise HTTPException(
            status_code=409, detail="Candidate failed artifact or metric checks"
        ) from error

    deployment = await session.get(DailyHealthModelDeployment, "daily_health")
    if deployment is not None and deployment.active_version_id == version.version_id:
        raise HTTPException(status_code=409, detail="Candidate is already active")
    if deployment is None:
        deployment = DailyHealthModelDeployment(
            deployment_key="daily_health",
            active_version_id=version.version_id,
            previous_version_id=None,
            approval_reason=payload.approval_reason.strip(),
        )
        session.add(deployment)
    else:
        deployment.previous_version_id = deployment.active_version_id
        deployment.active_version_id = version.version_id
        deployment.approval_reason = payload.approval_reason.strip()
    session.add(
        DailyHealthModelDeploymentEvent(
            action="promote",
            version_id=version.version_id,
            reason=payload.approval_reason.strip(),
        )
    )
    await session.commit()
    return {
        "active_version_id": deployment.active_version_id,
        "previous_version_id": deployment.previous_version_id,
        "approval_reason": deployment.approval_reason,
    }


@router.post("/model-deployment/rollback")
async def rollback_daily_health_model(
    payload: DailyHealthModelRollbackRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    deployment = await session.get(DailyHealthModelDeployment, "daily_health")
    if deployment is None or deployment.previous_version_id is None:
        raise HTTPException(
            status_code=409, detail="There is no previous candidate model to restore"
        )
    target = await session.get(DailyHealthModelVersion, deployment.previous_version_id)
    if target is None or target.status != "candidate":
        raise HTTPException(
            status_code=409, detail="The previous candidate is no longer deployable"
        )
    try:
        load_approved_candidate_bundle(target)
    except DailyHealthCandidateUnavailable as error:
        raise HTTPException(
            status_code=409, detail="Previous candidate failed artifact checks"
        ) from error

    current_version_id = deployment.active_version_id
    deployment.active_version_id = target.version_id
    deployment.previous_version_id = current_version_id
    deployment.approval_reason = payload.reason.strip()
    session.add(
        DailyHealthModelDeploymentEvent(
            action="rollback",
            version_id=target.version_id,
            reason=payload.reason.strip(),
        )
    )
    await session.commit()
    return {
        "active_version_id": deployment.active_version_id,
        "previous_version_id": deployment.previous_version_id,
        "approval_reason": deployment.approval_reason,
    }


@user_router.delete("/users/{user_id}/training-consent", status_code=204)
async def revoke_daily_health_model_training_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version.in_(MODEL_TRAINING_CONSENT_VERSIONS),
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    deployment = await session.get(DailyHealthModelDeployment, "daily_health")
    stale_statement = update(DailyHealthModelVersion).where(
        DailyHealthModelVersion.status.in_(["training", "candidate"])
    )
    if deployment is not None and deployment.active_version_id is not None:
        stale_statement = stale_statement.where(
            DailyHealthModelVersion.version_id != deployment.active_version_id
        )
    await session.execute(stale_statement.values(status="stale"))
    await session.commit()


@user_router.put("/users/{user_id}/outcomes", response_model=DailyHealthOutcomeRead)
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
        reported_dryness_level_0_10=payload.reported_dryness_level_0_10,
        updated_at=func.now(),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthOutcome.user_id, DailyHealthOutcome.target_date],
        set_={
            "reported_energy_level_0_10": statement.excluded.reported_energy_level_0_10,
            "reported_thirst_level_0_10": statement.excluded.reported_thirst_level_0_10,
            "reported_dryness_level_0_10": statement.excluded.reported_dryness_level_0_10,
            "updated_at": func.now(),
        },
    ).returning(DailyHealthOutcome)

    result = await session.execute(statement)
    outcome = result.scalar_one()
    await session.commit()
    return DailyHealthOutcomeRead.model_validate(outcome)


async def require_active_consent(
    session: AsyncSession, user_id: UUID, version: str = DAILY_HEALTH_CONSENT_VERSION
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    active = await session.scalar(
        select(Consent.id).where(
            Consent.user_id == user_id,
            Consent.version == version,
            Consent.revoked_at.is_(None),
        ).limit(1)
    )
    if active is None:
        raise HTTPException(status_code=403, detail=f"Active {version} consent is required")


@user_router.put("/users/{user_id}/profile", response_model=DailyHealthProfileRead)
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


@user_router.put("/users/{user_id}/age-band", response_model=DailyHealthAgeBandRead)
async def upsert_daily_health_age_band(
    user_id: UUID,
    payload: DailyHealthAgeBandUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthAgeBandRead:
    await require_active_consent(session, user_id, AGE_GUIDANCE_CONSENT_VERSION)
    statement = insert(DailyHealthAgeBand).values(user_id=user_id, **payload.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[DailyHealthAgeBand.user_id],
        set_={"age_band": statement.excluded.age_band, "updated_at": func.now()},
    ).returning(DailyHealthAgeBand)
    age_band = (await session.execute(statement)).scalar_one()
    await session.commit()
    return DailyHealthAgeBandRead.model_validate(age_band)


@user_router.put(
    "/users/{user_id}/menstrual-checkins", response_model=DailyHealthMenstrualCheckinRead
)
async def upsert_menstrual_checkin(
    user_id: UUID,
    payload: DailyHealthMenstrualCheckinUpsert,
    session: AsyncSession = Depends(get_session),
) -> DailyHealthMenstrualCheckinRead:
    await require_active_consent(session, user_id, PERSONALIZATION_CONSENT_VERSION)
    statement = insert(DailyHealthMenstrualCheckIn).values(user_id=user_id, **payload.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[
            DailyHealthMenstrualCheckIn.user_id,
            DailyHealthMenstrualCheckIn.local_date,
        ],
        set_={"currently_menstruating": statement.excluded.currently_menstruating},
    ).returning(DailyHealthMenstrualCheckIn)
    checkin = (await session.execute(statement)).scalar_one()
    await session.commit()
    return DailyHealthMenstrualCheckinRead.model_validate(checkin)


@user_router.put("/users/{user_id}/menstrual-checkins/consent")
async def grant_menstrual_checkin_consent(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Record explicit consent before storing cycle-calendar check-ins."""
    active = await session.scalar(
        select(Consent.id)
        .where(
            Consent.user_id == user_id,
            Consent.version == PERSONALIZATION_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active is None:
        session.add(Consent(user_id=user_id, version=PERSONALIZATION_CONSENT_VERSION))
        await session.commit()
    return {"status": "granted"}


@user_router.get(
    "/users/{user_id}/menstrual-checkins", response_model=list[DailyHealthMenstrualCheckinRead]
)
async def list_menstrual_checkins(
    user_id: UUID,
    limit: int = Query(default=28, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> list[DailyHealthMenstrualCheckinRead]:
    """Return only the caller's consented menstrual check-ins, newest first."""
    await require_active_consent(session, user_id, PERSONALIZATION_CONSENT_VERSION)
    records = (
        await session.scalars(
            select(DailyHealthMenstrualCheckIn)
            .where(DailyHealthMenstrualCheckIn.user_id == user_id)
            .order_by(
                DailyHealthMenstrualCheckIn.local_date.desc(),
                DailyHealthMenstrualCheckIn.id.desc(),
            )
            .limit(limit)
        )
    ).all()
    return [DailyHealthMenstrualCheckinRead.model_validate(record) for record in records]
