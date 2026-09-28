from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.auth import SignupRequest
from backend.api.schemas.consent import WellnessProfileUpsert
from backend.api.schemas.daily_health import DailyHealthEntryUpsert
from backend.api.v1.routes.auth import signup
from backend.core.db.models import Account, Consent, DailyHealthEntry, UserProfile


async def load_users(path: Path, session: AsyncSession) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise ValueError("Fixture must contain a users list")

    for row in data["users"]:
        user = SignupRequest.model_validate(row)
        profile = (
            WellnessProfileUpsert.model_validate(row["profile"])
            if "profile" in row else None
        )
        account = await session.scalar(select(Account).where(Account.email == user.email))
        user_id = account.user_id if account else (await signup(user, session)).user_id
        changed = False
        if profile is not None:
            existing = await session.get(UserProfile, user_id)
            if existing is None:
                session.add(UserProfile(user_id=user_id, **profile.profile_values()))
                changed = True

        entries = row.get("daily_entries", [])
        if entries:
            consent = await session.scalar(
                select(Consent.id).where(
                    Consent.user_id == user_id,
                    Consent.version == "daily-health-v1",
                    Consent.revoked_at.is_(None),
                ).limit(1)
            )
            if consent is None:
                session.add(Consent(user_id=user_id, version="daily-health-v1"))
                changed = True
            for entry in entries:
                DailyHealthEntryUpsert.model_validate(entry)
                if entry["data_source"] != "fixture":
                    raise ValueError("Fixture daily entries must use data_source=fixture")
                score = round(min(100.0, entry["sleep_duration_minutes"] / 540 * 100), 1)
                if entry["sleep_score_0_100"] != score:
                    raise ValueError("Fixture sleep score does not match its duration")
                statement = insert(DailyHealthEntry).values(user_id=user_id, **entry)
                inserted_id = await session.scalar(
                    statement.on_conflict_do_nothing(
                        index_elements=[DailyHealthEntry.user_id, DailyHealthEntry.local_date]
                    ).returning(DailyHealthEntry.id)
                )
                changed = changed or inserted_id is not None
        if changed:
            await session.commit()
