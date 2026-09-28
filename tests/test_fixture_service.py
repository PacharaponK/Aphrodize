from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.core.db.models import Questionnaire
from backend.services import fixture_service


@pytest.mark.asyncio
async def test_fixture_populates_questionnaire_once_for_existing_account(monkeypatch) -> None:
    user_id = uuid4()

    class Session:
        def __init__(self) -> None:
            self.questionnaire = None
            self.commits = 0

        async def scalar(self, query):
            if "accounts" in str(query):
                return SimpleNamespace(user_id=user_id)
            return self.questionnaire

        def add(self, questionnaire):
            self.questionnaire = questionnaire

        async def commit(self):
            self.commits += 1

    async def unexpected_signup(*_args):
        pytest.fail("Existing account must not be recreated")

    monkeypatch.setattr(fixture_service, "signup", unexpected_signup)
    session = Session()
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "users.yaml"
    await fixture_service.load_users(fixture, session)
    await fixture_service.load_users(fixture, session)

    assert isinstance(session.questionnaire, Questionnaire)
    assert session.questionnaire.user_id == user_id
    assert session.questionnaire.answers["skin_type"] == "combination"
    assert session.questionnaire.answers["menstrual_tracking"] == "yes"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_fixture_creates_account_and_questionnaire(monkeypatch) -> None:
    user_id = uuid4()
    created = []

    class Session:
        questionnaire = None

        async def scalar(self, _query):
            return None

        def add(self, questionnaire):
            self.questionnaire = questionnaire

        async def commit(self):
            pass

    async def fake_signup(user, _session):
        created.append(user)
        return SimpleNamespace(user_id=user_id)

    monkeypatch.setattr(fixture_service, "signup", fake_signup)
    session = Session()
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "users.yaml"
    await fixture_service.load_users(fixture, session)

    assert created[0].email == "demo@example.local"
    assert session.questionnaire.user_id == user_id
