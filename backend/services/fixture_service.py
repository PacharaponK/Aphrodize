from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.auth import SignupRequest
from backend.api.schemas.consent import InitialWellnessQuestionnaire
from backend.api.v1.routes.auth import signup
from backend.core.db.models import Account, Questionnaire


async def load_users(path: Path, session: AsyncSession) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise ValueError("Fixture must contain a users list")

    for row in data["users"]:
        user = SignupRequest.model_validate(row)
        questionnaire = (
            InitialWellnessQuestionnaire.model_validate(row["questionnaire"])
            if "questionnaire" in row else None
        )
        account = await session.scalar(select(Account).where(Account.email == user.email))
        user_id = account.user_id if account else (await signup(user, session)).user_id
        if questionnaire is not None:
            existing = await session.scalar(
                select(Questionnaire).where(Questionnaire.user_id == user_id)
                .order_by(Questionnaire.created_at.asc()).limit(1)
            )
            if existing is None:
                answers = questionnaire.answers_for_storage()
                session.add(Questionnaire(user_id=user_id, answers=answers))
                await session.commit()
