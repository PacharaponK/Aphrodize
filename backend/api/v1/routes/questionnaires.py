from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_api_credentials, require_user_token
from backend.api.schemas import (
    InitialWellnessQuestionnaire,
    QuestionnaireCreate,
    SafetyScreeningUpdate,
)
from backend.core.db.models import Questionnaire, User, UserProfile
from backend.core.db.session import get_session

router = APIRouter()


async def sync_profile_compatibility(session: AsyncSession, user_id: UUID, answers: dict) -> None:
    """Keep the profile refactor populated while retaining questionnaire history."""
    values = {
        key: answers[key]
        for key in (
            "sex",
            "age_group",
            "skin_type",
            "wellness_goal",
            "sunscreen_frequency",
            "menstrual_tracking",
        )
        if key in answers
    }
    if len(values) != 6:
        return
    statement = insert(UserProfile).values(user_id=user_id, **values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[UserProfile.user_id],
            set_={**{key: getattr(statement.excluded, key) for key in values}},
        )
    )


def latest_questionnaire_query(user_id: UUID):
    """Use the same stable ordering everywhere questionnaire history is read."""
    return (
        select(Questionnaire)
        .where(Questionnaire.user_id == user_id)
        .order_by(Questionnaire.created_at.desc(), Questionnaire.id.desc())
    )


@router.get("/initial")
async def get_initial_questionnaire(
    user_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    latest = await session.scalar(latest_questionnaire_query(user_id).limit(1))
    if latest is None:
        raise HTTPException(status_code=404, detail="Initial health questionnaire not found")
    return {"id": str(latest.id), "answers": latest.answers}


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
        raise HTTPException(
            status_code=409, detail="Initial health questionnaire already completed"
        )
    answers = payload.answers_for_storage()
    questionnaire = Questionnaire(user_id=user_id, answers=answers)
    session.add(questionnaire)
    await sync_profile_compatibility(session, user_id, answers)
    await session.commit()
    return {"id": str(questionnaire.id), "status": "saved"}


@router.put("/initial")
async def update_initial_questionnaire(
    payload: InitialWellnessQuestionnaire,
    user_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Append a revised self-report without mutating questionnaire history."""
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    if payload.base_revision_id is None:
        raise HTTPException(status_code=422, detail="A base questionnaire revision is required")
    latest = await session.scalar(latest_questionnaire_query(user_id).with_for_update().limit(1))
    if latest is None:
        raise HTTPException(
            status_code=409, detail="Complete the initial health questionnaire first"
        )
    if latest.id != payload.base_revision_id:
        raise HTTPException(
            status_code=409,
            detail="Questionnaire changed elsewhere. Reload it before saving your edits.",
        )
    answers = payload.answers_for_storage()
    questionnaire = Questionnaire(user_id=user_id, answers=answers)
    session.add(questionnaire)
    await sync_profile_compatibility(session, user_id, answers)
    await session.commit()
    return {"id": str(questionnaire.id), "status": "updated"}


@router.put("/initial/safety")
async def update_safety_screening(
    payload: SafetyScreeningUpdate,
    user_id: UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Append a safety-only revision, preserving all previously reported answers."""
    latest = await session.scalar(latest_questionnaire_query(user_id).with_for_update().limit(1))
    if latest is None:
        raise HTTPException(
            status_code=409, detail="Complete the initial health questionnaire first"
        )
    if latest.id != payload.base_revision_id:
        raise HTTPException(
            status_code=409,
            detail="Questionnaire changed elsewhere. Reload it before saving your edits.",
        )
    answers = {**latest.answers, **payload.safety_answers()}
    if payload.known_product_allergy != "yes":
        answers.pop("allergy_details", None)
    questionnaire = Questionnaire(user_id=user_id, answers=answers)
    session.add(questionnaire)
    await session.commit()
    return {"id": str(questionnaire.id), "status": "updated"}


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
