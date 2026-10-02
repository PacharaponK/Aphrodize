from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.schemas.consent import WellnessProfileUpsert
from backend.api.v1.routes.auth import (
    grant_daily_health_consent,
    save_wellness_profile,
    skin_profile,
)
from backend.api.v1.routes.auth import (
    router as auth_router,
)
from backend.api.v1.routes.questionnaires import router as questionnaire_router
from backend.core.db.base import Base
from backend.core.db.models import Account, Consent, Questionnaire, User, UserProfile


def profile_payload(**changes):
    return WellnessProfileUpsert.model_validate(
        {
            "sex": "female",
            "age_group": "25_34",
            "skin_type": "combination",
            "wellness_goal": "skin_tracking",
            "sunscreen_frequency": "every_day",
            "menstrual_tracking": "yes",
            **changes,
        }
    )


def test_profile_schema_coexists_with_questionnaire_compatibility_and_validates_guardian() -> None:
    assert "questionnaires" in Base.metadata.tables
    assert any(route.path == "/profile" and "PUT" in route.methods for route in auth_router.routes)
    assert any(
        route.path == "/initial" and "POST" in route.methods
        for route in questionnaire_router.routes
    )
    assert Questionnaire.__table__.columns["user_id"].index is True
    assert UserProfile.__table__.primary_key.columns.keys() == ["user_id"]
    assert profile_payload().profile_values()["skin_type"] == "combination"
    assert profile_payload(sex="male").profile_values()["menstrual_tracking"] == "not_applicable"
    with pytest.raises(ValidationError):
        profile_payload(age_group="under_13")


@pytest.mark.asyncio
async def test_profile_upsert_requires_consent_and_records_guardian_consent() -> None:
    user_id = uuid4()

    class Session:
        def __init__(self, consent):
            self.consent = consent
            self.scalar_calls = 0
            self.added = []
            self.executed = None
            self.committed = False

        async def get(self, model, _user_id):
            return User() if model is User else None

        async def scalar(self, _query):
            self.scalar_calls += 1
            return self.consent if self.scalar_calls == 1 else None

        def add(self, value):
            self.added.append(value)

        async def execute(self, statement):
            self.executed = statement

        async def commit(self):
            self.committed = True

    without_consent = Session(None)
    with pytest.raises(HTTPException) as error:
        await save_wellness_profile(profile_payload(), user_id, without_consent)
    assert error.value.status_code == 403
    assert without_consent.executed is None

    session = Session(uuid4())
    result = await save_wellness_profile(
        profile_payload(age_group="under_13", guardian_consent=True), user_id, session
    )
    assert result == {"status": "saved"}
    assert session.committed
    assert any(
        isinstance(value, Consent) and value.version == "guardian-health-v1"
        for value in session.added
    )
    assert "ON CONFLICT" in str(session.executed)


@pytest.mark.asyncio
async def test_account_profile_exposes_identity_and_daily_consent_is_idempotent() -> None:
    user_id = uuid4()

    class Session:
        def __init__(self):
            self.consent_exists = False
            self.added = []
            self.commits = 0

        async def scalar(self, query):
            if "accounts" in str(query):
                return Account(display_name="A", email="a@example.com")
            return uuid4() if self.consent_exists else None

        async def get(self, model, _user_id):
            return None

        def add(self, value):
            self.added.append(value)
            self.consent_exists = True

        async def commit(self):
            self.commits += 1

    session = Session()
    profile = await skin_profile(user_id, session)
    assert profile.user_id == user_id
    assert (await grant_daily_health_consent(user_id, session))["status"] == "granted"
    assert (await grant_daily_health_consent(user_id, session))["status"] == "granted"
    assert session.commits == 1
    assert len(session.added) == 1
    assert isinstance(session.added[0], Consent)
    assert session.added[0].version == "daily-health-v1"

    class MissingAccount(Session):
        async def scalar(self, query):
            if "accounts" in str(query):
                return None
            return await super().scalar(query)

    missing_account = MissingAccount()
    with pytest.raises(HTTPException) as error:
        await grant_daily_health_consent(user_id, missing_account)
    assert error.value.status_code == 401
    assert missing_account.added == []
