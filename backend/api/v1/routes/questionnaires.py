from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_api_credentials, require_user_token
from backend.api.schemas import InitialWellnessQuestionnaire, QuestionnaireCreate
from backend.core.db.models import Questionnaire, User
from backend.core.db.session import get_session

router = APIRouter()


@router.post("/initial", status_code=status.HTTP_201_CREATED)
async def save_initial_questionnaire(
    payload: InitialWellnessQuestionnaire,
    user_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    existing = await session.scalar(
        select(Questionnaire.id).where(Questionnaire.user_id == user_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Initial health questionnaire already completed")
    questionnaire = Questionnaire(user_id=user_id, answers=payload.answers_for_storage())
    session.add(questionnaire)
    await session.commit()
    return {"id": str(questionnaire.id), "status": "saved"}


@router.post("/users/{user_id}", status_code=status.HTTP_201_CREATED)
async def save_questionnaire(
    user_id: UUID,
    payload: QuestionnaireCreate,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_api_credentials),
) -> dict[str, str]:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    questionnaire = Questionnaire(user_id=user_id, answers=payload.answers)
    session.add(questionnaire)
    await session.commit()
    return {"id": str(questionnaire.id), "status": "saved"}
