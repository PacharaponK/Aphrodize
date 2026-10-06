from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_matching_user
from backend.api.schemas.acne import AcneConsentInput, AcneInput, AcneRead, AcneTrainingConsentInput
from backend.core.config import settings
from backend.core.consents import (
    ACNE_MODEL_TRAINING_CONSENT_VERSION,
    ACNE_TRACKING_CONSENT_VERSION,
)
from backend.core.db.models import AcneObservation, Consent, User
from backend.core.db.session import get_session

VERSION = ACNE_TRACKING_CONSENT_VERSION


def private_response(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(dependencies=[Depends(require_matching_user), Depends(private_response)])


async def owner(session: AsyncSession, user_id: UUID) -> None:
    # Serialize consent/save/delete operations for a given owner, including withdrawal.
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or user.status != "active":
        raise HTTPException(404, "Active user not found")


def enabled() -> None:
    if not settings.acne_tracking_enabled:
        raise HTTPException(503, "Acne tracking is not enabled")


async def consent_active(session: AsyncSession, user_id: UUID, version: str = VERSION) -> bool:
    return (
        await session.scalar(
            select(Consent.id)
            .where(
                Consent.user_id == user_id, Consent.version == version, Consent.revoked_at.is_(None)
            )
            .limit(1)
        )
        is not None
    )


@router.get("/users/{user_id}")
async def history(
    user_id: UUID,
    limit: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await owner(session, user_id)
    if not settings.acne_tracking_enabled:
        return {"enabled": False, "consent_active": False, "items": []}
    active = await consent_active(session, user_id)
    training = await consent_active(session, user_id, ACNE_MODEL_TRAINING_CONSENT_VERSION)
    rows = []
    if active:
        rows = (
            await session.scalars(
                select(AcneObservation)
                .where(AcneObservation.user_id == user_id)
                .order_by(AcneObservation.local_date.desc())
                .limit(limit)
            )
        ).all()
    return {
        "enabled": True,
        "consent_active": active,
        "training_consent_active": training,
        "items": [AcneRead.model_validate(row).model_dump(mode="json") for row in rows],
    }


@router.put("/users/{user_id}/consent")
async def grant(
    user_id: UUID,
    payload: AcneConsentInput,
    session: AsyncSession = Depends(get_session),
) -> dict:
    enabled()
    await owner(session, user_id)
    if not await consent_active(session, user_id):
        session.add(Consent(user_id=user_id, version=VERSION))
    await session.commit()
    return {"consent_active": True}


@router.put("/users/{user_id}/training-consent")
async def grant_training(
    user_id: UUID,
    payload: AcneTrainingConsentInput,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await owner(session, user_id)
    raise HTTPException(410, "Acne model training has been removed")


@router.delete("/users/{user_id}/training-consent", status_code=204)
async def withdraw_training(user_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    await owner(session, user_id)
    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == ACNE_MODEL_TRAINING_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    # Legacy withdrawal remains available after removal. Keep observations.
    await session.commit()


@router.delete("/users/{user_id}/consent", status_code=204)
async def withdraw(user_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    # Allow cleanup even if collection is later disabled. Never touch other scopes.
    await owner(session, user_id)
    await session.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version.in_([VERSION, ACNE_MODEL_TRAINING_CONSENT_VERSION]),
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await session.execute(delete(AcneObservation).where(AcneObservation.user_id == user_id))
    await session.commit()


@router.put("/users/{user_id}/observations", response_model=AcneRead)
async def save(
    user_id: UUID,
    payload: AcneInput,
    session: AsyncSession = Depends(get_session),
) -> AcneRead:
    enabled()
    if payload.local_date > datetime.now(ZoneInfo("Asia/Bangkok")).date():
        raise HTTPException(422, "Future observations are not allowed")
    await owner(session, user_id)
    if not await consent_active(session, user_id):
        raise HTTPException(403, "Separate acne storage consent is required")
    row = await session.scalar(
        select(AcneObservation).where(
            AcneObservation.user_id == user_id, AcneObservation.local_date == payload.local_date
        )
    )
    if row is None:
        row = AcneObservation(
            user_id=user_id,
            **payload.model_dump(),
            provenance="user_reported",
            consent_version=VERSION,
        )
        session.add(row)
    else:
        row.response = payload.response
        row.regions = payload.regions
    await session.commit()
    await session.refresh(row)
    return AcneRead.model_validate(row)


@router.delete("/users/{user_id}/observations/{local_date}", status_code=204)
async def remove(
    user_id: UUID,
    local_date: date,
    session: AsyncSession = Depends(get_session),
) -> None:
    await owner(session, user_id)
    await session.execute(
        delete(AcneObservation).where(
            AcneObservation.user_id == user_id, AcneObservation.local_date == local_date
        )
    )
    await session.commit()
