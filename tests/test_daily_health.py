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
    DailyHealthProfileHeightUpsert,
)
from backend.api.v1.routes.daily_health import (
    delete_daily_health_profile,
    delete_daily_health_profile_height,
    list_daily_health_entries,
    read_daily_health_profile,
    revoke_daily_health_model_training_consent,
    upsert_daily_health_entry,
    upsert_daily_health_outcome,
    upsert_daily_health_profile_height,
)
from backend.core.db.models import (
    Consent,
    DailyHealthAgeBand,
    DailyHealthEntry,
    DailyHealthMenstrualCheckIn,
    DailyHealthOutcome,
    DailyHealthProfile,
    User,
)


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
        {"sleep_duration_minutes": 601},
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


@pytest.mark.parametrize("height_cm", [29.9, 300.1, float("inf")])
def test_height_profile_rejects_invalid_measurements(height_cm: float) -> None:
    with pytest.raises(ValidationError):
        DailyHealthProfileHeightUpsert(height_cm=height_cm, consent_given=True)


def test_height_profile_requires_explicit_consent() -> None:
    with pytest.raises(ValidationError):
        DailyHealthProfileHeightUpsert(height_cm=168, consent_given=False)


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

    dryness_only = DailyHealthOutcomeUpsert(
        target_date=date(2026, 9, 26),
        reported_dryness_level_0_10=4.5,
    )
    assert dryness_only.reported_dryness_level_0_10 == 4.5


def test_training_consent_is_separate_and_off_by_default() -> None:
    entry = DailyHealthEntryUpsert(
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=360,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
    )

    assert entry.model_training_consent is False


def test_prediction_target_date_only_allows_same_day_or_next_day() -> None:
    base = {
        "local_date": date(2026, 9, 26),
        "sleep_duration_minutes": 360,
        "water_intake_ml": 1400,
        "outdoor_exposure_choice": 1,
    }

    allowed = DailyHealthEntryUpsert(
        **base,
        prediction={
            "thirst_score_0_10": 4,
            "dryness_score_0_10": 5,
            "prediction_status": "predicted",
            "target_date": date(2026, 9, 27),
        },
    )
    assert allowed.prediction.target_date == date(2026, 9, 27)

    with pytest.raises(ValidationError, match="following day"):
        DailyHealthEntryUpsert(
            **base,
            prediction={
                "thirst_score_0_10": 4,
                "dryness_score_0_10": 5,
                "prediction_status": "predicted",
                "target_date": date(2026, 9, 28),
            },
        )


def test_daily_health_prediction_accepts_sleep_through_10_hours_only() -> None:
    payload = DailyHealthPredictionRequest(
        local_date=date(2026, 9, 26),
        sleep_hours=10,
        sleep_minutes=0,
        water_intake_ml=700,
        outdoor_exposure_choice=1,
    )

    assert payload.water_intake_ml == 700
    assert payload.sleep_hours == 10
    with pytest.raises(ValidationError):
        DailyHealthPredictionRequest(
            local_date=date(2026, 9, 26),
            sleep_hours=10,
            sleep_minutes=1,
            water_intake_ml=1400,
            outdoor_exposure_choice=1,
        )


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeSession:
    def __init__(
        self,
        entry: DailyHealthEntry,
        has_consent: bool = True,
        has_training_consent: bool = False,
        has_outcome: bool = False,
        profile_weight_kg: float | None = None,
        profile_height_cm: float | None = None,
    ) -> None:
        self.entry = entry
        self.has_consent = has_consent
        self.has_training_consent = has_training_consent
        self.has_outcome = has_outcome
        self.profile_weight_kg = profile_weight_kg
        self.profile_height_cm = profile_height_cm
        self.committed = False
        self.statement = None
        self.statements = []
        self.added = []

    async def get(self, model, _user_id):
        if model is DailyHealthProfile and (
            self.profile_weight_kg is not None or self.profile_height_cm is not None
        ):
            return DailyHealthProfile(
                user_id=uuid4(),
                weight_kg=self.profile_weight_kg,
                height_cm=self.profile_height_cm,
            )
        return object() if model is User else None

    async def scalar(self, statement):
        if "daily_health_outcomes" in str(statement):
            return uuid4() if self.has_outcome else None
        params = statement.compile().params.values()
        if "daily-health-model-training-v1" in params:
            return uuid4() if self.has_training_consent else None
        return uuid4() if self.has_consent else None

    async def execute(self, statement):
        self.statement = statement
        self.statements.append(statement)
        return FakeResult(self.entry)

    async def commit(self):
        self.committed = True

    def add(self, item):
        self.added.append(item)


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
        weight_kg=60,
        calculated_thirst_score_0_10=2.2,
        thirst_score_method="recorded-fluid-shortfall-weight-v1",
        outdoor_exposure_choice=1,
        sleep_score_0_100=67.0,
        sleep_score_method=(
            "round(min(100, sleep_duration_minutes / 540 * 100), 1); duration-only, 9h cap"
        ),
        predicted_thirst_score_0_10=4.2,
        predicted_dryness_score_0_10=3.8,
        prediction_target_date=date(2026, 9, 27),
        prediction_status="predicted",
        prediction_model_id="daily-score-random-forest-synthetic-v1",
        data_source="user_reported",
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(entry, profile_weight_kg=60)
    payload = DailyHealthEntryUpsert(
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=362,
        water_intake_ml=1400,
        weight_kg=80,
        outdoor_exposure_choice=1,
        prediction={
            "thirst_score_0_10": 4.2,
            "dryness_score_0_10": 3.8,
            "prediction_status": "predicted",
            "model_id": "daily-score-random-forest-synthetic-v1",
            "target_date": date(2026, 9, 27),
        },
    )

    result = await upsert_daily_health_entry(user_id, payload, session)

    compiled = str(session.statement.compile(dialect=postgresql.dialect())).upper()
    assert "ON CONFLICT" in compiled
    assert session.committed is True
    assert result.sleep_score_0_100 == 67.0
    assert result.predicted_thirst_score_0_10 == 4.2
    assert result.prediction_target_date == date(2026, 9, 27)
    assert result.training_eligible is False
    params = session.statement.compile().params
    assert params["weight_kg"] == 60
    assert params["calculated_thirst_score_0_10"] == 2.2
    assert params["thirst_score_method"] == "recorded-fluid-shortfall-weight-v1"
    assert result.calculated_thirst_score_0_10 == 2.2


@pytest.mark.asyncio
async def test_entry_eligibility_uses_next_day_outcome_and_training_consent() -> None:
    user_id = uuid4()
    entry = DailyHealthEntry(
        id=uuid4(), user_id=user_id, local_date=date(2026, 9, 26),
        timezone="Asia/Bangkok", sleep_duration_minutes=360, water_intake_ml=1400,
        outdoor_exposure_choice=1, sleep_score_0_100=66.7,
        sleep_score_method="duration", predicted_thirst_score_0_10=4.2,
        predicted_dryness_score_0_10=3.8, prediction_target_date=date(2026, 9, 27),
        prediction_status="predicted", prediction_model_id="test", data_source="user_reported",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    payload = DailyHealthEntryUpsert(
        local_date=entry.local_date, sleep_duration_minutes=360,
        water_intake_ml=1400, outdoor_exposure_choice=1,
    )
    session = FakeSession(entry, has_training_consent=True, has_outcome=True)
    result = await upsert_daily_health_entry(user_id, payload, session)
    assert result.training_eligible is True

    session = FakeSession(entry, has_training_consent=True, has_outcome=False)
    result = await upsert_daily_health_entry(user_id, payload, session)
    assert result.training_eligible is False


@pytest.mark.asyncio
async def test_daily_entry_can_grant_separate_opt_in_for_model_training() -> None:
    user_id = uuid4()
    entry = DailyHealthEntry(
        id=uuid4(),
        user_id=user_id,
        local_date=date(2026, 9, 26),
        timezone="Asia/Bangkok",
        sleep_duration_minutes=360,
        water_intake_ml=1400,
        outdoor_exposure_choice=1,
        sleep_score_0_100=66.7,
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
        model_training_consent=True,
    )

    await upsert_daily_health_entry(user_id, payload, session)

    assert any(
        isinstance(item, Consent) and item.version == "daily-health-model-training-v1"
        for item in session.added
    )
    assert session.committed is True


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


def test_predictions_are_not_training_labels() -> None:
    entry = DailyHealthEntry(
        predicted_thirst_score_0_10=4.2,
        predicted_dryness_score_0_10=3.8,
        reported_thirst_score_0_10=None,
        reported_dryness_score_0_10=None,
    )
    assert entry.training_eligible is False


def test_both_reported_scores_enable_training() -> None:
    entry = DailyHealthEntry(
        reported_thirst_score_0_10=5.0,
        reported_dryness_score_0_10=4.0,
    )
    assert entry.training_eligible is True


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
        str(item.compile(dialect=postgresql.dialect())).upper() for item in session.statements
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
        "model_training_consent_active": False,
        "can_report_outcomes": False,
        "age_band": None,
        "smoking_status": None,
        "weight_profile_consent_active": False,
        "weight_kg": None,
        "height_profile_consent_active": False,
        "height_cm": None,
    }


@pytest.mark.asyncio
async def test_profile_read_returns_height_when_height_consent_is_active() -> None:
    session = FakeSession(DailyHealthEntry(), profile_height_cm=168)

    result = await read_daily_health_profile(uuid4(), session)

    assert result["height_profile_consent_active"] is True
    assert result["height_cm"] == 168


@pytest.mark.asyncio
async def test_height_profile_upsert_requires_and_records_consent() -> None:
    session = FakeSession(DailyHealthEntry(), has_consent=False)
    payload = DailyHealthProfileHeightUpsert(height_cm=168, consent_given=True)

    result = await upsert_daily_health_profile_height(uuid4(), payload, session)

    statement = str(session.statement.compile(dialect=postgresql.dialect())).upper()
    assert "ON CONFLICT" in statement
    assert "HEIGHT_CM" in statement
    assert result == {"height_profile_consent_active": True, "height_cm": 168}
    assert session.added[0].version == "daily-health-height-profile-v1"
    assert session.committed is True


@pytest.mark.asyncio
async def test_height_profile_delete_revokes_consent() -> None:
    session = FakeSession(DailyHealthEntry(), profile_height_cm=168)

    await delete_daily_health_profile_height(uuid4(), session)

    statement = str(session.statement.compile(dialect=postgresql.dialect())).upper()
    params = session.statement.compile().params.values()
    assert "UPDATE CONSENTS" in statement
    assert "daily-health-height-profile-v1" in params
    assert session.committed is True


@pytest.mark.asyncio
async def test_profile_delete_removes_sensitive_context_and_revokes_consent() -> None:
    session = FakeSession(DailyHealthEntry())

    await delete_daily_health_profile(uuid4(), session)

    statements = [
        str(item.compile(dialect=postgresql.dialect())).upper() for item in session.statements
    ]
    assert any("DELETE FROM DAILY_HEALTH_PROFILES" in statement for statement in statements)
    assert any("DELETE FROM DAILY_HEALTH_AGE_BANDS" in statement for statement in statements)
    assert any(
        "DELETE FROM DAILY_HEALTH_MENSTRUAL_CHECKINS" in statement for statement in statements
    )
    assert any("UPDATE CONSENTS" in statement for statement in statements)
    assert session.committed is True


@pytest.mark.asyncio
async def test_training_consent_can_be_revoked_without_deleting_daily_history() -> None:
    session = FakeSession(DailyHealthEntry())

    await revoke_daily_health_model_training_consent(uuid4(), session)

    statements = [item.compile(dialect=postgresql.dialect()) for item in session.statements]
    assert any("UPDATE CONSENTS" in str(statement).upper() for statement in statements)
    assert any(
        "UPDATE DAILY_HEALTH_MODEL_VERSIONS" in str(statement).upper() for statement in statements
    )
    assert any(
        "DAILY_HEALTH_MODEL_VERSIONS.STATUS IN" in str(statement).upper()
        for statement in statements
    )
    assert any(
        "daily-health-model-training-v1" in statement.params.values() for statement in statements
    )
    assert session.committed is True


class FakeScalarList:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeDailyHealthHistorySession:
    def __init__(
        self,
        entries,
        *,
        active_consents: set[str] | None = None,
        profile=None,
        age_band=None,
        menstrual_checkins=None,
    ):
        self.entries = entries
        self.active_consents = (
            active_consents if active_consents is not None else {"daily-health-v1"}
        )
        self.profile = profile
        self.age_band = age_band
        self.menstrual_checkins = menstrual_checkins or []
        self.scalars_calls = []
        self.entry_query_params = None

    async def get(self, model, _user_id):
        if model is User:
            return object()
        if model.__name__ == "DailyHealthProfile":
            return self.profile
        if model.__name__ == "DailyHealthAgeBand":
            return self.age_band
        return None

    async def scalar(self, statement):
        params = set(statement.compile().params.values())
        consent_version = next(
            (version for version in self.active_consents if version in params), None
        )
        return object() if consent_version is not None else None

    async def scalars(self, statement):
        query = str(statement).lower()
        self.scalars_calls.append(query)
        if "daily_health_entries" in query:
            self.entry_query_params = statement.compile().params
            return FakeScalarList(self.entries)
        if "daily_health_menstrual_checkins" in query:
            return FakeScalarList(self.menstrual_checkins)
        return FakeScalarList([])


@pytest.mark.asyncio
async def test_history_read_returns_saved_prediction_risks_with_consented_profile_context() -> None:
    user_id = uuid4()
    entry = DailyHealthEntry(
        id=uuid4(),
        user_id=user_id,
        local_date=date(2026, 9, 26),
        timezone="Asia/Bangkok",
        sleep_duration_minutes=330,
        water_intake_ml=1200,
        outdoor_exposure_choice=2,
        sleep_score_0_100=61.1,
        sleep_score_method="duration-only",
        predicted_thirst_score_0_10=8.0,
        predicted_dryness_score_0_10=8.0,
        prediction_target_date=date(2026, 9, 27),
        prediction_status="predicted",
        prediction_model_id="daily-score-test-v1",
        data_source="user_reported",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = FakeDailyHealthHistorySession(
        [entry],
        active_consents={
            "daily-health-v1",
            "daily-health-personalization-v1",
            "daily-health-age-guidance-v1",
        },
        profile=DailyHealthProfile(user_id=user_id, smoking_status="current"),
        age_band=DailyHealthAgeBand(user_id=user_id, age_band="18_60"),
        menstrual_checkins=[
            DailyHealthMenstrualCheckIn(
                user_id=user_id,
                local_date=date(2026, 9, 26),
                currently_menstruating=True,
            )
        ],
    )

    result = await list_daily_health_entries(user_id, limit=7, session=session)

    item = result["items"][0]
    assert item["local_date"] == "2026-09-26"
    assert item["prediction_target_date"] == "2026-09-27"
    assert item["interpretation"]["daily_health_summary"]["level"] == "high"
    assert item["interpretation"]["skin_care_attention_level"]["level"] == "high"
    assert {item["topic"] for item in item["interpretation"]["profile_guidance"]} == {
        "smoking",
        "menstrual_wellbeing",
    }
    assert "user_id" not in item


@pytest.mark.asyncio
async def test_history_read_does_not_return_rows_without_daily_health_consent() -> None:
    session = FakeDailyHealthHistorySession([DailyHealthEntry()], active_consents=set())

    result = await list_daily_health_entries(uuid4(), limit=7, session=session)

    assert result == {"items": []}
    assert not session.scalars_calls


@pytest.mark.asyncio
async def test_history_preserves_formula_snapshot_and_independent_dryness_prediction() -> None:
    user_id = uuid4()
    entry = DailyHealthEntry(
        user_id=user_id,
        local_date=date(2026, 9, 26),
        sleep_duration_minutes=480,
        water_intake_ml=900,
        weight_kg=60,
        calculated_thirst_score_0_10=5.0,
        thirst_score_method="recorded-fluid-shortfall-weight-v1",
        outdoor_exposure_choice=1,
        sleep_score_0_100=88.9,
        prediction_status="predicted",
        predicted_thirst_score_0_10=None,
        predicted_dryness_score_0_10=2.0,
        prediction_target_date=date(2026, 9, 27),
    )
    result = await list_daily_health_entries(
        user_id,
        limit=7,
        session=FakeDailyHealthHistorySession([entry]),
    )
    item = result["items"][0]
    assert item["predictions"]["thirst_score_0_10"]["value"] == 5
    assert item["predictions"]["thirst_score_0_10"]["status"] == "calculated"
    assert item["predictions"]["thirst_score_0_10"]["target_date"] == "2026-09-26"
    assert item["predictions"]["skin_dryness_score_0_10"]["value"] == 2
    assert item["prediction_target_date"] == "2026-09-27"
    assert item["input"]["weight_kg"] == 60
    assert item["interpretation"]["skin_care_attention_level"]["level"] == "low"


@pytest.mark.asyncio
async def test_history_read_can_be_scoped_to_a_local_calendar_date_window() -> None:
    user_id = uuid4()
    start_date = date(2026, 9, 20)
    end_date = date(2026, 9, 26)
    session = FakeDailyHealthHistorySession([])

    result = await list_daily_health_entries(
        user_id,
        limit=7,
        from_date=start_date,
        to_date=end_date,
        session=session,
    )

    assert result == {"items": []}
    assert start_date in session.entry_query_params.values()
    assert end_date in session.entry_query_params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("from_date", "to_date", "detail"),
    [
        (date(2026, 9, 20), None, "Both from_date and to_date are required together"),
        (date(2026, 9, 27), date(2026, 9, 20), "from_date must not be after to_date"),
        (date(2026, 1, 1), date(2026, 4, 1), "Date window cannot exceed 90 days"),
    ],
)
async def test_history_read_rejects_invalid_date_windows(from_date, to_date, detail) -> None:
    with pytest.raises(HTTPException, match=detail):
        await list_daily_health_entries(
            uuid4(),
            from_date=from_date,
            to_date=to_date,
            session=FakeDailyHealthHistorySession([]),
        )


@pytest.mark.asyncio
async def test_daily_health_outcome_is_upserted_only_with_active_daily_consent() -> None:
    user_id = uuid4()
    outcome = DailyHealthOutcome(
        id=uuid4(),
        user_id=user_id,
        target_date=date.today(),
        reported_energy_level_0_10=6.0,
        reported_thirst_level_0_10=3.0,
        reported_dryness_level_0_10=4.5,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = FakeSession(outcome)
    payload = DailyHealthOutcomeUpsert(
        target_date=date.today(),
        reported_energy_level_0_10=6,
        reported_thirst_level_0_10=3,
        reported_dryness_level_0_10=4.5,
    )

    result = await upsert_daily_health_outcome(user_id, payload, session)

    compiled = str(session.statement.compile(dialect=postgresql.dialect())).upper()
    assert "ON CONFLICT" in compiled
    assert "REPORTED_DRYNESS_LEVEL_0_10" in compiled
    assert result.reported_energy_level_0_10 == 6
    assert result.reported_thirst_level_0_10 == 3
    assert result.reported_dryness_level_0_10 == 4.5
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
