from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import QuestionnaireCreate
from backend.core.db.models import Questionnaire, User
from backend.core.db.session import get_session

router = APIRouter()


@router.post("/users/{user_id}", status_code=status.HTTP_201_CREATED)
async def save_questionnaire(
    user_id: UUID, payload: QuestionnaireCreate, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    questionnaire = Questionnaire(user_id=user_id, answers=payload.answers)
    session.add(questionnaire)
    await session.commit()
    return {"id": str(questionnaire.id), "status": "saved"}
