import uuid

from fastapi import APIRouter, Depends, status
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
    session.add_all([user, consent])
    await session.commit()
    await session.refresh(consent)
    return ConsentRead(
        user_id=user.id,
        consent_id=consent.id,
        version=consent.version,
        accepted_at=consent.accepted_at,
    )
