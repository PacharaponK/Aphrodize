import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_matching_user
from backend.api.schemas import ConsentCreate, ConsentRead
from backend.core.config import settings
from backend.core.db.models import Consent, User
from backend.core.db.session import get_session
from backend.services.analysis_service import ANALYSIS_CONSENT_VERSION
from backend.services.annotation_service import ANNOTATION_CONSENT_VERSION, delete_user_annotations
from backend.services.tokens import create_access_token

router = APIRouter()
user_router = APIRouter(dependencies=[Depends(require_matching_user)])


@router.post("", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
async def create_consent(
    payload: ConsentCreate, session: AsyncSession = Depends(get_session)
) -> ConsentRead:
    # Create an anonymous user ID for this upload rather than reusing a browser account.
    user = User(id=uuid.uuid4())
    # Link the requested analysis consent version to that new user.
    consent = Consent(user_id=user.id, version=payload.version)
    # Flush the user first so the consent foreign key can refer to it.
    session.add(user)
    await session.flush()
    session.add(consent)
    # Commit both records together and reload server-generated timestamps.
    await session.commit()
    await session.refresh(consent)
    return ConsentRead(
        user_id=user.id,
        consent_id=consent.id,
        version=consent.version,
        accepted_at=consent.accepted_at,
        access_token=create_access_token(user.id, expires_minutes=30 * 24 * 60),
    )


@user_router.get("/users/{user_id}")
async def read_image_consents(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict[str, bool]:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    versions = await session.scalars(
        select(Consent.version).where(
            Consent.user_id == user_id,
            Consent.version.in_([ANALYSIS_CONSENT_VERSION, ANNOTATION_CONSENT_VERSION]),
            Consent.revoked_at.is_(None),
        )
    )
    active = set(versions.all())
    return {
        "analysis": ANALYSIS_CONSENT_VERSION in active,
        "annotations": ANNOTATION_CONSENT_VERSION in active,
    }


@user_router.delete("/users/{user_id}/analysis", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_analysis_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    await session.execute(
        Consent.__table__.update()
        .where(Consent.user_id == user_id, Consent.version == ANALYSIS_CONSENT_VERSION)
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


@user_router.put("/users/{user_id}/analysis")
async def grant_analysis_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = await session.scalar(
        select(Consent.id).where(
            Consent.user_id == user_id,
            Consent.version == ANALYSIS_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        ).limit(1)
    )
    if existing is None:
        session.add(Consent(user_id=user_id, version=ANALYSIS_CONSENT_VERSION))
        await session.commit()
    return {"status": "granted"}


# Review consent is separate from the consent required to run image analysis.
@user_router.post(
    "/users/{user_id}/annotations",
    response_model=ConsentRead,
    status_code=status.HTTP_201_CREATED,
)
async def grant_annotation_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> ConsentRead:
    # A review consent cannot be attached to an unknown user.
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Do not accept review consent before a Label Studio token and project are set.
    if not settings.label_studio_api_key or settings.label_studio_project_id < 1:
        raise HTTPException(status_code=503, detail="Annotation review is not configured")
    # Reuse an active consent so repeated requests do not create duplicates.
    existing = await session.scalar(
        select(Consent).where(
            Consent.user_id == user_id,
            Consent.version == ANNOTATION_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
    )
    consent = existing or Consent(user_id=user_id, version=ANNOTATION_CONSENT_VERSION)
    if existing is None:
        # Persist only when no active review consent already exists.
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
    return ConsentRead(
        user_id=user_id,
        consent_id=consent.id,
        version=consent.version,
        accepted_at=consent.accepted_at,
    )


@user_router.delete("/users/{user_id}/annotations", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_annotation_consent(
    user_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Mark every review consent for this user revoked before touching stored images.
    await session.execute(
        Consent.__table__.update()
        .where(Consent.user_id == user_id, Consent.version == ANNOTATION_CONSENT_VERSION)
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    try:
        # Remove staged images and corresponding Label Studio tasks.
        await delete_user_annotations(session, user_id)
    except Exception as error:
        # The worker can retry cleanup when Label Studio becomes available again.
        raise HTTPException(
            status_code=503, detail="Annotation deletion is pending; retry"
        ) from error
