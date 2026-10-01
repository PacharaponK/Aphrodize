from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml
from sqlalchemy.sql.dml import Insert

from backend.core.db.models import (
    Consent,
    DailyHealthDatasetRecord,
    DailyHealthEntry,
    UserProfile,
)
from backend.services import fixture_service

FIXTURE = Path(__file__).resolve().parents[1] / "backend" / "fixtures" / "users.yaml"


class FakeSession:
    def __init__(self, user_id, *, account_exists=True):
        self.user_id = user_id
        self.account_exists = account_exists
        self.profile = None
        self.consent = None
        self.entries = {}
        self.dataset_records = {}
        self.commits = 0

    async def scalar(self, query):
        if isinstance(query, Insert):
            values = query.compile().params
            if query.table.name == DailyHealthDatasetRecord.__tablename__:
                key = (values["dataset_fingerprint"], values["source_row_number"])
                if key in self.dataset_records:
                    return None
                self.dataset_records[key] = values
                return uuid4()
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

    row = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["users"][0]
    assert created[0].email == row["email"].strip().lower()
    assert session.profile.user_id == user_id
    assert len(session.entries) == 2


@pytest.mark.asyncio
async def test_fixture_preserves_imported_tracker_rows_and_is_idempotent(tmp_path) -> None:
    record = {
        "local_date": "2026-09-12",
        "data_origin": "real_user_tracker_xlsx",
        "source_user_id": 1,
        "source_local_date_raw": "12/9/20026",
        "source_sleep_duration_hours_raw": "no recorded",
        "source_sleep_duration_mins_raw": "no recorded",
        "skin_dryness_level": 0.2,
        "skin_feeling_status": "oil",
        "outdoor_minutes": 1,
    }
    path = tmp_path / "users.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "users": [],
                "daily_health_dataset": {
                    "source_dataset_name": "real_user_tracker_xlsx",
                    "records": [record],
                },
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(uuid4())

    await fixture_service.load_users(path, session)
    await fixture_service.load_users(path, session)

    assert len(session.dataset_records) == 1
    values = next(iter(session.dataset_records.values()))
    assert values["participant_key"] == "participant_0001"
    assert values["training_eligible"] is False
    assert values["record_payload"]["source_user_id"] == "participant_0001"
    assert values["record_payload"]["source_local_date_raw"] == "12/9/20026"
    assert values["record_payload"]["source_sleep_duration_hours_raw"] == "no recorded"
    assert values["record_payload"]["skin_dryness_level"] == 0.2
    assert session.commits == 1


@pytest.mark.asyncio
async def test_fixture_preserves_tester_water_data(tmp_path) -> None:
    record = {
        "local_date": "2026-09-30",
        "data_origin": "tester",
        "source_user_id": 8,
        "source_local_date_raw": "30/9/2026",
        "source_sleep_duration_hours_raw": 5,
        "source_sleep_duration_mins_raw": 34,
        "skin_dryness_level": 0.35,
        "skin_feeling_status": "oil",
        "outdoor_minutes": 1,
        "water_intake_ml": 1325,
    }
    path = tmp_path / "users.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "users": [],
                "daily_health_dataset": {
                    "source_dataset_name": "tester",
                    "records": [record],
                },
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(uuid4())

    await fixture_service.load_users(path, session)

    values = next(iter(session.dataset_records.values()))
    payload = values["record_payload"]
    assert payload["source_user_id"] == "participant_0001"
    assert payload["source_local_date_raw"] == "30/9/2026"
    assert payload["skin_feeling_status"] == "oil"
    assert payload["water_intake_ml"] == 1325
    assert values["training_eligible"] is False
