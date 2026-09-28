from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml
from sqlalchemy.sql.dml import Insert

from backend.core.db.models import Consent, DailyHealthEntry, UserProfile
from backend.services import fixture_service

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "users.yaml"


class FakeSession:
    def __init__(self, user_id, *, account_exists=True):
        self.user_id = user_id
        self.account_exists = account_exists
        self.profile = None
        self.consent = None
        self.entries = {}
        self.commits = 0

    async def scalar(self, query):
        if isinstance(query, Insert):
            values = query.compile().params
            key = (values["user_id"], values["local_date"])
            if key in self.entries:
                return None
            self.entries[key] = values
            return uuid4()
        if "FROM accounts" in str(query):
            return SimpleNamespace(user_id=self.user_id) if self.account_exists else None
        if "FROM consents" in str(query):
            return self.consent
        raise AssertionError(f"Unexpected query: {query}")

    async def get(self, _model, _user_id):
        return self.profile

    def add(self, value):
        if isinstance(value, UserProfile):
            self.profile = value
        elif isinstance(value, Consent):
            self.consent = value
        else:
            raise AssertionError(f"Unexpected model: {type(value)}")

    async def commit(self):
        self.commits += 1


def test_fixture_covers_profile_and_daily_entry_fields() -> None:
    row = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["users"][0]
    profile_fields = set(UserProfile.__table__.columns.keys()) - {"user_id", "updated_at"}
    entry_fields = set(DailyHealthEntry.__table__.columns.keys()) - {
        "id", "user_id", "created_at", "updated_at"
    }
    assert set(row["profile"]) - {"guardian_consent"} == profile_fields
    assert len(row["daily_entries"]) == 2
    assert all(set(entry) == entry_fields for entry in row["daily_entries"])


@pytest.mark.asyncio
async def test_fixture_populates_profile_and_two_days_once(monkeypatch) -> None:
    user_id = uuid4()

    async def unexpected_signup(*_args):
        pytest.fail("Existing account must not be recreated")

    monkeypatch.setattr(fixture_service, "signup", unexpected_signup)
    session = FakeSession(user_id)
    await fixture_service.load_users(FIXTURE, session)
    await fixture_service.load_users(FIXTURE, session)

    assert session.profile.user_id == user_id
    assert session.profile.skin_type == "combination"
    assert session.profile.menstrual_tracking == "yes"
    assert session.consent.version == "daily-health-v1"
    assert len(session.entries) == 2
    assert all(key[0] == user_id for key in session.entries)
    assert all(entry["data_source"] == "fixture" for entry in session.entries.values())
    assert session.commits == 1


@pytest.mark.asyncio
async def test_fixture_creates_account_profile_and_daily_entries(monkeypatch) -> None:
    user_id = uuid4()
    created = []

    async def fake_signup(user, _session):
        created.append(user)
        return SimpleNamespace(user_id=user_id)

    monkeypatch.setattr(fixture_service, "signup", fake_signup)
    session = FakeSession(user_id, account_exists=False)
    await fixture_service.load_users(FIXTURE, session)

    assert created[0].email == "demo@example.local"
    assert session.profile.user_id == user_id
    assert len(session.entries) == 2
