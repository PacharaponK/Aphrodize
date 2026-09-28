from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.schemas.consent import WellnessProfileUpsert
from backend.api.v1.router import api_router
from backend.api.v1.routes.auth import save_wellness_profile
from backend.core.db.base import Base
from backend.core.db.models import Consent, User, UserProfile


def profile_payload(**changes):
    return WellnessProfileUpsert.model_validate({
        "sex": "female",
        "age_group": "25_34",
        "skin_type": "combination",
        "wellness_goal": "skin_tracking",
        "sunscreen_frequency": "every_day",
        "menstrual_tracking": "yes",
        **changes,
    })


def test_profile_schema_replaces_questionnaire_and_validates_guardian() -> None:
    assert "questionnaires" not in Base.metadata.tables
    assert any(
        route.path == "/auth/profile" and "PUT" in route.methods
        for route in api_router.routes
    )
    assert not any(route.path.startswith("/questionnaires") for route in api_router.routes)
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
