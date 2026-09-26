from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from backend.api.schemas.daily_health import (
    DailyHealthEntryUpsert,
    DailyHealthOutcomeUpsert,
    DailyHealthPersonalContext,
    DailyHealthPredictionRequest,
)
from backend.api.v1.routes.daily_health import (
    delete_daily_health_profile,
    read_daily_health_profile,
    upsert_daily_health_entry,
    upsert_daily_health_outcome,
)
from backend.core.db.models import DailyHealthEntry, DailyHealthOutcome, User


def test_daily_health_entry_accepts_tracker_choices_and_optional_prediction() -> None:
    entry = DailyHealthEntryUpsert(
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=362,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
        prediction=None,
    )

    assert entry.timezone == "Asia/Bangkok"
    assert entry.sleep_duration_minutes == 362
    assert entry.prediction is None


@pytest.mark.parametrize(
    "values",
    [
        {"sleep_duration_minutes": 541},
        {"water_intake_ml": 20_001},
        {"outdoor_exposure_choice": 5},
    ],
)
def test_daily_health_entry_rejects_values_outside_tracker_bounds(values: dict) -> None:
    payload = {
        "local_date": date(2026, 9, 26),
        "sleep_duration_minutes": 360,
        "water_intake_ml": 1400,
        "outdoor_exposure_choice": 1,
        **values,
    }

    with pytest.raises(ValidationError):
        DailyHealthEntryUpsert(**payload)


def test_personal_context_requires_explicit_consent() -> None:
    with pytest.raises(ValidationError):
        DailyHealthPersonalContext(consent_given=False, smoking_status="current")

    with pytest.raises(ValidationError):
        DailyHealthEntryUpsert(
            local_date=date(2026, 9, 26),
            sleep_duration_minutes=360,
            water_intake_ml=1400,
            outdoor_exposure_choice=1,
            smoking_status="current",
        )

    with pytest.raises(ValidationError):
        DailyHealthPersonalContext(
            consent_given=False,
            age_band="65_plus",
            age_guidance_consent_given=False,
        )

    age_context = DailyHealthPersonalContext(
        age_guidance_consent_given=True,
        age_band="65_plus",
    )
    assert age_context.age_band == "65_plus"

    with pytest.raises(ValidationError):
        DailyHealthEntryUpsert(
            local_date=date(2026, 9, 26),
            sleep_duration_minutes=360,
            water_intake_ml=1400,
            outdoor_exposure_choice=1,
            age_guidance_consent=False,
            age_band="18_60",
        )


def test_reported_outcome_requires_at_least_one_real_observed_score() -> None:
    with pytest.raises(ValidationError):
        DailyHealthOutcomeUpsert(
            target_date=date(2026, 9, 26),
            reported_energy_level_0_10=None,
            reported_thirst_level_0_10=None,
        )

    outcome = DailyHealthOutcomeUpsert(
        target_date=date(2026, 9, 26),
        reported_energy_level_0_10=6,
        reported_thirst_level_0_10=None,
    )
    assert outcome.reported_energy_level_0_10 == 6


def test_daily_health_prediction_accepts_only_physically_valid_out_of_training_values() -> None:
    payload = DailyHealthPredictionRequest(
        local_date=date(2026, 9, 26),
        sleep_hours=6,
        sleep_minutes=0,
        water_intake_ml=700,
        outdoor_exposure_choice=1,
    )

    assert payload.water_intake_ml == 700
    with pytest.raises(ValidationError):
        DailyHealthPredictionRequest(
            local_date=date(2026, 9, 26),
            sleep_hours=9,
            sleep_minutes=1,
            water_intake_ml=1400,
            outdoor_exposure_choice=1,
        )


def test_model_predictions_are_not_eligible_training_labels() -> None:
    entry = DailyHealthEntry(
        predicted_thirst_score_0_10=4.2,
        predicted_dryness_score_0_10=3.8,
        reported_thirst_score_0_10=None,
        reported_dryness_score_0_10=None,
    )

    assert entry.training_eligible is False


def test_entry_becomes_training_eligible_only_with_both_reported_scores() -> None:
    entry = DailyHealthEntry(
        predicted_thirst_score_0_10=4.2,
        predicted_dryness_score_0_10=3.8,
        reported_thirst_score_0_10=5.0,
        reported_dryness_score_0_10=4.0,
    )

    assert entry.training_eligible is True


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeSession:
    def __init__(self, entry: DailyHealthEntry, has_consent: bool = True) -> None:
        self.entry = entry
        self.has_consent = has_consent
        self.committed = False
        self.statement = None
        self.statements = []

    async def get(self, model, _user_id):
        return object() if model is User else None

    async def scalar(self, _statement):
        return uuid4() if self.has_consent else None

    async def execute(self, statement):
        self.statement = statement
        self.statements.append(statement)
        return FakeResult(self.entry)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_daily_health_route_upserts_only_with_consent_and_calculates_sleep_score() -> None:
    user_id = uuid4()
    now = datetime.now(UTC)
    entry = DailyHealthEntry(
        id=uuid4(),
        user_id=user_id,
        local_date=date(2026, 9, 26),
        timezone="Asia/Bangkok",
        sleep_duration_minutes=362,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
        sleep_score_0_100=86.2,
        sleep_score_method="min(100, sleep_duration_minutes / 420 * 100); duration-only",
        predicted_thirst_score_0_10=4.2,
        predicted_dryness_score_0_10=3.8,
        prediction_status="predicted",
        prediction_model_id="daily-score-random-forest-synthetic-v1",
        data_source="user_reported",
        reported_thirst_score_0_10=None,
        reported_dryness_score_0_10=None,
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(entry)
    payload = DailyHealthEntryUpsert(
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=362,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
        prediction={
            "thirst_score_0_10": 4.2,
            "dryness_score_0_10": 3.8,
            "prediction_status": "predicted",
            "model_id": "daily-score-random-forest-synthetic-v1",
        },
    )

    result = await upsert_daily_health_entry(user_id, payload, session)

    compiled = str(session.statement.compile(dialect=postgresql.dialect())).upper()
    assert "ON CONFLICT" in compiled
    assert session.committed is True
    assert result.sleep_score_0_100 == 86.2
    assert result.predicted_thirst_score_0_10 == 4.2
    assert result.training_eligible is False


@pytest.mark.asyncio
async def test_daily_health_route_requires_active_consent() -> None:
    session = FakeSession(DailyHealthEntry(), has_consent=False)
    payload = DailyHealthEntryUpsert(
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=360,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
    )

    with pytest.raises(HTTPException) as error:
        await upsert_daily_health_entry(uuid4(), payload, session)

    assert error.value.status_code == 403
    assert session.committed is False


@pytest.mark.asyncio
async def test_daily_health_route_stores_personal_context_only_with_separate_consent() -> None:
    entry = DailyHealthEntry(
        id=uuid4(),
        user_id=uuid4(),
        local_date=date(2026, 9, 26),
        timezone="Asia/Bangkok",
        sleep_duration_minutes=360,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
        sleep_score_0_100=85.7,
        sleep_score_method="duration-only",
        prediction_status="not_run",
        data_source="user_reported",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = FakeSession(entry)
    payload = DailyHealthEntryUpsert(
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=360,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
        personalization_consent=True,
        age_guidance_consent=True,
        age_band="18_60",
        smoking_status="current",
        currently_menstruating=True,
    )

    await upsert_daily_health_entry(entry.user_id, payload, session)

    statements = [
        str(item.compile(dialect=postgresql.dialect())).upper()
        for item in session.statements
    ]
    assert any("DAILY_HEALTH_PROFILES" in statement for statement in statements)
    assert any("DAILY_HEALTH_AGE_BANDS" in statement for statement in statements)
    assert any("DAILY_HEALTH_MENSTRUAL_CHECKINS" in statement for statement in statements)
    assert session.committed is True


@pytest.mark.asyncio
async def test_profile_read_hides_data_when_personalization_consent_is_inactive() -> None:
    session = FakeSession(DailyHealthEntry(), has_consent=False)

    result = await read_daily_health_profile(uuid4(), session)

    assert result == {
        "consent_active": False,
        "age_guidance_consent_active": False,
        "can_report_outcomes": False,
        "age_band": None,
        "smoking_status": None,
    }


@pytest.mark.asyncio
async def test_profile_delete_removes_sensitive_context_and_revokes_consent() -> None:
    session = FakeSession(DailyHealthEntry())

    await delete_daily_health_profile(uuid4(), session)

    statements = [
        str(item.compile(dialect=postgresql.dialect())).upper()
        for item in session.statements
    ]
    assert any("DELETE FROM DAILY_HEALTH_PROFILES" in statement for statement in statements)
    assert any("DELETE FROM DAILY_HEALTH_AGE_BANDS" in statement for statement in statements)
    assert any(
        "DELETE FROM DAILY_HEALTH_MENSTRUAL_CHECKINS" in statement
        for statement in statements
    )
    assert any("UPDATE CONSENTS" in statement for statement in statements)
    assert session.committed is True


@pytest.mark.asyncio
async def test_daily_health_outcome_is_upserted_only_with_active_daily_consent() -> None:
    user_id = uuid4()
    outcome = DailyHealthOutcome(
        id=uuid4(),
        user_id=user_id,
        target_date=date.today(),
        reported_energy_level_0_10=6.0,
        reported_thirst_level_0_10=3.0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = FakeSession(outcome)
    payload = DailyHealthOutcomeUpsert(
        target_date=date.today(),
        reported_energy_level_0_10=6,
        reported_thirst_level_0_10=3,
    )

    result = await upsert_daily_health_outcome(user_id, payload, session)

    compiled = str(session.statement.compile(dialect=postgresql.dialect())).upper()
    assert "ON CONFLICT" in compiled
    assert result.reported_energy_level_0_10 == 6
    assert result.reported_thirst_level_0_10 == 3
    assert session.committed is True


@pytest.mark.asyncio
async def test_daily_health_outcome_requires_active_daily_consent() -> None:
    session = FakeSession(DailyHealthOutcome(), has_consent=False)
    payload = DailyHealthOutcomeUpsert(
        target_date=date.today(),
        reported_energy_level_0_10=5,
    )

    with pytest.raises(HTTPException) as error:
        await upsert_daily_health_outcome(uuid4(), payload, session)

    assert error.value.status_code == 403
    assert session.committed is False
