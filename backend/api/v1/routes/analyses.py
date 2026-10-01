from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_matching_user, require_user_token
from backend.api.schemas.analysis import AnalysisRead
from backend.core.db.models import (
    Analysis,
    AnalysisStatus,
    Consent,
    DailyHealthEntry,
    DailyHealthOutcome,
    Product,
    Questionnaire,
    User,
    UserProfile,
)
from backend.core.db.session import get_session
from backend.libs.minio_client import analysis_artifact_key, get_bytes
from backend.services.analysis_service import (
    attach_catalog_products,
    create_analysis,
    recommendations_for,
)

DAILY_HEALTH_CONSENT_VERSION = "daily-health-v1"
DAILY_CONTEXT_MAX_AGE_DAYS = 30

router = APIRouter()


async def recommendation_context(
    session: AsyncSession, user_id: UUID
) -> tuple[Questionnaire | None, dict[str, object]]:
    """Load only consented, recent, user-reported data for recommendation rules."""
    questionnaire = await session.scalar(
        select(Questionnaire)
        .where(Questionnaire.user_id == user_id)
        .order_by(Questionnaire.created_at.desc(), Questionnaire.id.desc())
        .limit(1)
    )
    daily_context: dict[str, object] = {"status": "not_consented"}
    daily_consent = await session.scalar(
        select(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == DAILY_HEALTH_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .order_by(Consent.accepted_at.desc(), Consent.id.desc())
        .limit(1)
    )
    if daily_consent is None:
        return questionnaire, daily_context

    today = date.today()
    since = today - timedelta(days=DAILY_CONTEXT_MAX_AGE_DAYS)
    lifestyle_entry = await session.scalar(
        select(DailyHealthEntry)
        .where(
            DailyHealthEntry.user_id == user_id,
            DailyHealthEntry.local_date.between(since, today),
            DailyHealthEntry.data_source == "user_reported",
        )
        .order_by(DailyHealthEntry.local_date.desc(), DailyHealthEntry.id.desc())
        .limit(1)
    )
    outcome = await session.scalar(
        select(DailyHealthOutcome)
        .where(
            DailyHealthOutcome.user_id == user_id,
            DailyHealthOutcome.target_date.between(since, today),
            DailyHealthOutcome.reported_dryness_level_0_10.is_not(None),
        )
        .order_by(DailyHealthOutcome.target_date.desc(), DailyHealthOutcome.id.desc())
        .limit(1)
    )
    daily_context = {
        "status": "no_recent_reported_dryness",
        "consent": {"record_id": str(daily_consent.id), "version": daily_consent.version},
    }
    if lifestyle_entry is not None:
        daily_context["lifestyle"] = {
            "source_table": "daily_health_entries",
            "record_id": str(lifestyle_entry.id),
            "observed_date": lifestyle_entry.local_date.isoformat(),
            "sleep_duration_minutes": lifestyle_entry.sleep_duration_minutes,
            "water_intake_ml": lifestyle_entry.water_intake_ml,
            "outdoor_exposure_choice": lifestyle_entry.outdoor_exposure_choice,
        }
    if outcome is not None and outcome.reported_dryness_level_0_10 is not None:
        daily_context.update({
            "status": "available",
            "reported_dryness": {
                "source_table": "daily_health_outcomes",
                "record_id": str(outcome.id),
                "observed_date": outcome.target_date.isoformat(),
                "value": outcome.reported_dryness_level_0_10,
            },
        })
    return questionnaire, daily_context


def questionnaire_context(questionnaire: Questionnaire | None) -> dict[str, str | None]:
    return {
        "status": "available" if questionnaire is not None else "missing",
        "revision_id": str(questionnaire.id) if questionnaire is not None else None,
    }


async def recommendation_response(
    session: AsyncSession, user_id: UUID, analysis: Analysis | None = None,
    *, market: str = "TH", max_price_satang: int | None = None,
) -> dict:
    if analysis is not None and analysis.status != AnalysisStatus.completed:
        response = recommendations_for(analysis, {})
        response["questionnaire_context"] = questionnaire_context(None)
        attach_catalog_products(response, [])
        return response
    consent = await session.scalar(select(Consent.id).where(
        Consent.user_id == user_id, Consent.version == "signup-v1",
        Consent.revoked_at.is_(None),
    ).limit(1))
    if consent is None:
        response = recommendations_for(analysis, {})
        response["blocked_reason"] = "profile_consent_required"
        response["questionnaire_context"] = questionnaire_context(None)
        attach_catalog_products(response, [])
        return response
    questionnaire, daily_context = await recommendation_context(session, user_id)
    answers = dict(questionnaire.answers) if questionnaire else {}
    profile = await session.get(UserProfile, user_id)
    if profile is not None:
        # The editable profile is authoritative; safety answers stay in questionnaire history.
        if profile.age_group != answers.get("age_group"):
            answers.pop("age_years", None)
        answers.update({key: getattr(profile, key) for key in (
            "sex", "age_group", "skin_type", "sunscreen_frequency",
        )})
    response = recommendations_for(analysis, answers, daily_context)
    response["questionnaire_context"] = questionnaire_context(questionnaire)
    if response.get("profile_context") is not None:
        response["profile_context"]["source"] = "user_profile" if profile else "questionnaire"
    products = []
    if response["status"] == "ready" and not response["allergy_context"]["reported"]:
        # ponytail: scan at most 500 reviewed catalog entries; paginate if the catalog grows.
        products = list((await session.scalars(
            select(Product).where(
                Product.status == "published", Product.reviewed_at.is_not(None),
            ).order_by(Product.reviewed_at.desc(), Product.id).limit(500)
        )).all())
    attach_catalog_products(
        response, products, market=market if market != "all" else None,
        max_price_satang=max_price_satang,
    )
    return response


def serialize(analysis: Analysis) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        status=analysis.status.value,
        model_family=analysis.model_family,
        model_version=analysis.model_version,
        image_quality_score=analysis.image_quality_score,
        quality_flags=analysis.quality_flags or [],
        result=analysis.result,
        error_category=analysis.error_category,
        created_at=analysis.created_at,
    )


# A 202 response means the analysis was accepted or rejected by preflight, not that AI finished.
@router.post("/users/{user_id}", response_model=AnalysisRead, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis(
    user_id: UUID,
    image: UploadFile = File(...),
    _: UUID = Depends(require_matching_user),
    session: AsyncSession = Depends(get_session),
) -> AnalysisRead:
    # Validate the user path parameter before the service reads the image.
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    # The service performs consent, image, storage, and queue checks.
    analysis = await create_analysis(session, user_id, image)
    return serialize(analysis)


@router.get("/recommendations")
async def get_profile_recommendations(
    user_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
    market: Literal["TH", "all"] = "TH",
    max_price_satang: Annotated[int | None, Query(ge=0, le=100_000_000)] = None,
) -> dict:
    """Recommend from the latest self-reported profile even when no image exists."""
    return await recommendation_response(
        session, user_id, market=market, max_price_satang=max_price_satang,
    )


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: UUID,
    caller_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> AnalysisRead:
    # The result page polls this row while the worker changes its status.
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != caller_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return serialize(analysis)


@router.get("/{analysis_id}/artifacts/{kind}")
async def get_analysis_artifact(
    analysis_id: UUID,
    kind: Literal["overlay", "mask"],
    caller_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> Response:
    # Display artifacts are available only when the analysis has a result.
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != caller_id or not analysis.result:
        raise HTTPException(status_code=404, detail="Artifact not found")
    expiry_text = analysis.result.get("artifacts_expires_at")
    # No expiry field means no viewable artifact was published.
    if not isinstance(expiry_text, str):
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        # Parse the timestamp written by the inference worker.
        expires_at = datetime.fromisoformat(expiry_text)
    except ValueError as error:
        raise HTTPException(status_code=410, detail="Artifact expired") from error
    if expires_at.tzinfo is None or datetime.now(UTC) >= expires_at:
        # Refuse expired images even if the delayed deletion job has not run.
        raise HTTPException(status_code=410, detail="Artifact expired")
    # Construct the private MinIO key from the stored user and analysis IDs.
    key = analysis_artifact_key(analysis.user_id, analysis.id, kind)
    try:
        content = await run_in_threadpool(get_bytes, key)
    except S3Error as error:
        raise HTTPException(status_code=404, detail="Artifact not found") from error
    return Response(content, media_type="image/png", headers={"Cache-Control": "private, no-store"})


@router.get("/{analysis_id}/recommendations")
async def get_recommendations(
    analysis_id: UUID,
    user_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
    market: Literal["TH", "all"] = "TH",
    max_price_satang: Annotated[int | None, Query(ge=0, le=100_000_000)] = None,
) -> dict:
    # Keep account data private: the bearer token must own the requested analysis.
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != user_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return await recommendation_response(
        session, user_id, analysis, market=market, max_price_satang=max_price_satang,
    )
