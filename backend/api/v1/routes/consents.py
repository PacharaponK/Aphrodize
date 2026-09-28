import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import ConsentCreate, ConsentRead
from backend.core.db.models import Consent, User
from backend.core.db.session import get_session

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


@router.post("/users/{user_id}", response_model=ConsentRead)
async def add_consent_to_user(
    user_id: uuid.UUID,
    payload: ConsentCreate,
    session: AsyncSession = Depends(get_session),
) -> ConsentRead:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    consent = await session.scalar(
        select(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == payload.version,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if consent is None:
        consent = Consent(user_id=user_id, version=payload.version)
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
    return ConsentRead(
        user_id=user_id,
        consent_id=consent.id,
        version=consent.version,
        accepted_at=consent.accepted_at,
    )
