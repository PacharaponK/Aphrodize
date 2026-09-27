import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import ConsentCreate, ConsentRead
from backend.core.config import settings
from backend.core.db.models import Consent, User
from backend.core.db.session import get_session
from backend.services.annotation_service import ANNOTATION_CONSENT_VERSION, delete_user_annotations

router = APIRouter()


@router.post("", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
async def create_consent(
    payload: ConsentCreate, session: AsyncSession = Depends(get_session)
) -> ConsentRead:
    user = User(id=uuid.uuid4())
    consent = Consent(user_id=user.id, version=payload.version)
    session.add(user)
    await session.flush()
    session.add(consent)
    await session.commit()
    await session.refresh(consent)
    return ConsentRead(
        user_id=user.id,
        consent_id=consent.id,
        version=consent.version,
        accepted_at=consent.accepted_at,
    )


@router.post(
    "/users/{user_id}/annotations",
    response_model=ConsentRead,
    status_code=status.HTTP_201_CREATED,
)
async def grant_annotation_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> ConsentRead:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not settings.label_studio_api_key or settings.label_studio_project_id < 1:
        raise HTTPException(status_code=503, detail="Annotation review is not configured")
    existing = await session.scalar(
        select(Consent).where(
            Consent.user_id == user_id,
            Consent.version == ANNOTATION_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
    )
    consent = existing or Consent(user_id=user_id, version=ANNOTATION_CONSENT_VERSION)
    if existing is None:
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
    return ConsentRead(
        user_id=user_id,
        consent_id=consent.id,
        version=consent.version,
        accepted_at=consent.accepted_at,
    )


@router.delete("/users/{user_id}/annotations", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_annotation_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    await session.execute(
        Consent.__table__.update()
        .where(Consent.user_id == user_id, Consent.version == ANNOTATION_CONSENT_VERSION)
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    try:
        await delete_user_annotations(session, user_id)
    except Exception as error:
        raise HTTPException(
            status_code=503, detail="Annotation deletion is pending; retry"
        ) from error
