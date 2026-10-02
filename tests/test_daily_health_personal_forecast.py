from datetime import date, timedelta
from uuid import uuid4

import pytest

from backend.api.v1.routes import daily_health as daily_health_routes
from backend.api.v1.routes.daily_health import (
    get_personal_daily_health_forecast,
    grant_personal_daily_health_forecast_consent,
    revoke_personal_daily_health_forecast_consent,
)
from backend.core.db.models import DailyHealthEntry
from backend.services.daily_health_personal_forecast import (
    build_personal_daily_health_forecast,
)


def _entry(
    user_id,
    local_date: date,
    sleep_minutes: int,
    water_ml: int,
    *,
    data_source: str = "user_reported",
) -> DailyHealthEntry:
    return DailyHealthEntry(
        user_id=user_id,
        local_date=local_date,
        timezone="Asia/Bangkok",
        sleep_duration_minutes=sleep_minutes,
        water_intake_ml=water_ml,
        outdoor_exposure_choice=1,
        sleep_score_0_100=round(min(100, sleep_minutes / 540 * 100), 1),
        sleep_score_method="test duration score",
        data_source=data_source,
    )


def test_forecast_uses_only_this_accounts_real_entries_in_the_last_seven_days() -> None:
    account_id = uuid4()
    another_account_id = uuid4()
    as_of_date = date(2026, 9, 30)
    entries = [
        _entry(
            account_id,
            as_of_date - timedelta(days=6 - offset),
            360 + offset * 10,
            1000 + offset * 100,
        )
        for offset in range(5)
    ]
    entries.extend(
        [
            _entry(account_id, as_of_date - timedelta(days=1), 590, 19_000, data_source="fixture"),
            _entry(account_id, as_of_date, 600, 20_000, data_source="fixture"),
            _entry(another_account_id, as_of_date, 100, 100, data_source="user_reported"),
            _entry(account_id, as_of_date - timedelta(days=7), 100, 100),
            _entry(account_id, as_of_date + timedelta(days=1), 100, 100),
        ]
    )

    result = build_personal_daily_health_forecast(
        entries,
        user_id=account_id,
        as_of_date=as_of_date,
    )

    assert result["status"] == "forecasted"
    assert result["prediction_target_date"] == "2026-10-01"
    assert result["model"]["scope"] == "account_only"
    assert result["model"]["observations_used"] == 5
    assert result["predictions"]["sleep_duration_minutes"] == {
        "value": 430,
        "status": "predicted",
    }
    assert result["predictions"]["water_intake_ml"] == {
        "value": 1700,
        "status": "predicted",
    }
    assert [point["sleep_duration_minutes"] for point in result["actual"]] == [
        360,
        370,
        380,
        390,
        400,
        None,
        None,
    ]


def test_forecast_abstains_when_account_has_fewer_than_three_actual_records() -> None:
    account_id = uuid4()
    as_of_date = date(2026, 9, 30)
    entries = [
        _entry(account_id, as_of_date - timedelta(days=offset), 360, 1200)
        for offset in (0, 2)
    ]

    result = build_personal_daily_health_forecast(
        entries,
        user_id=account_id,
        as_of_date=as_of_date,
    )

    assert result["status"] == "insufficient_history"
    assert result["predictions"]["sleep_duration_minutes"] == {
        "value": None,
        "status": "insufficient_history",
    }
    assert result["predictions"]["water_intake_ml"] == {
        "value": None,
        "status": "insufficient_history",
    }


class _ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _ForecastSession:
    def __init__(self, *, user_id, active_consents=(), entries=()):
        self.user_id = user_id
        self.active_consents = set(active_consents)
        self.entries = list(entries)
        self.history_query = None

    async def get(self, model, user_id):
        return object() if model.__name__ == "User" and user_id == self.user_id else None

    async def scalar(self, statement):
        params = statement.compile().params.values()
        consent_version = next(
            (
                value
                for value in params
                if isinstance(value, str) and value.startswith("daily-health-")
            ),
            None,
        )
        return consent_version if consent_version in self.active_consents else None

    async def scalars(self, statement):
        self.history_query = statement
        return _ScalarRows(self.entries)


class _MutableForecastSession(_ForecastSession):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.added = []
        self.executed = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def execute(self, statement):
        self.executed.append(statement)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_forecast_api_does_not_read_history_until_account_only_consent_is_active() -> None:
    account_id = uuid4()
    session = _ForecastSession(
        user_id=account_id,
        active_consents={"daily-health-v1"},
        entries=[_entry(account_id, date(2026, 9, 30), 420, 1500)],
    )

    result = await get_personal_daily_health_forecast(account_id, session)

    assert result["enabled"] is False
    assert result["status"] == "consent_required"
    assert session.history_query is None


@pytest.mark.asyncio
async def test_forecast_api_returns_next_day_estimates_after_account_only_opt_in(
    monkeypatch,
) -> None:
    account_id = uuid4()
    as_of_date = date(2026, 9, 30)
    monkeypatch.setattr(daily_health_routes, "_current_bangkok_date", lambda: as_of_date)
    entries = [
        _entry(account_id, as_of_date - timedelta(days=2), 360, 1200),
        _entry(account_id, as_of_date - timedelta(days=1), 390, 1300),
        _entry(account_id, as_of_date, 420, 1400),
        _entry(account_id, as_of_date, 600, 20_000, data_source="fixture"),
    ]
    session = _ForecastSession(
        user_id=account_id,
        active_consents={"daily-health-v1", "daily-health-personal-forecast-v1"},
        entries=entries,
    )

    result = await get_personal_daily_health_forecast(account_id, session)

    assert result["enabled"] is True
    assert result["status"] == "forecasted"
    assert result["prediction_target_date"] == "2026-10-01"
    assert result["predictions"]["sleep_duration_minutes"]["value"] == 450
    assert result["predictions"]["water_intake_ml"]["value"] == 1500
    assert result["model"]["scope"] == "account_only"
    query_values = session.history_query.compile().params.values()
    assert account_id in query_values
    assert "user_reported" in query_values


@pytest.mark.asyncio
async def test_account_forecast_consent_is_separate_from_shared_model_training_consent() -> None:
    account_id = uuid4()
    session = _MutableForecastSession(
        user_id=account_id,
        active_consents={"daily-health-v1"},
    )

    result = await grant_personal_daily_health_forecast_consent(account_id, session)

    assert result == {"enabled": True, "scope": "account_only"}
    assert session.committed is True
    assert [consent.version for consent in session.added] == [
        "daily-health-personal-forecast-v1"
    ]


@pytest.mark.asyncio
async def test_account_forecast_consent_can_be_revoked_without_revoking_other_consents() -> None:
    account_id = uuid4()
    session = _MutableForecastSession(user_id=account_id)

    await revoke_personal_daily_health_forecast_consent(account_id, session)

    assert session.committed is True
    assert len(session.executed) == 1
    revoked_params = session.executed[0].compile().params.values()
    assert "daily-health-personal-forecast-v1" in revoked_params
    assert "daily-health-model-training-v1" not in revoked_params
