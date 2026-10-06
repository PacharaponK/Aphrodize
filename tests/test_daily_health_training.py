from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SQLSession

from backend.core.db.models import Consent, DailyHealthEntry, DailyHealthOutcome, User
from backend.services.daily_health_training import (
    TrainingExample,
    build_next_day_training_examples,
    load_consent_filtered_training_examples,
    should_create_next_candidate,
    split_examples_by_participant,
)


def _entry(user_id, local_date: date) -> DailyHealthEntry:
    return DailyHealthEntry(
        user_id=user_id,
        local_date=local_date,
        sleep_duration_minutes=420,
        water_intake_ml=1500,
        outdoor_exposure_choice=2,
        data_source="user_reported",
        predicted_thirst_score_0_10=3.0,
        predicted_dryness_score_0_10=2.0,
        sleep_score_0_100=77.8,
        sleep_score_method="test-only",
        created_at=datetime.combine(local_date, datetime.min.time(), UTC),
        updated_at=datetime.combine(local_date, datetime.min.time(), UTC),
    )


def test_training_excludes_inputs_unavailable_at_bangkok_prediction_boundary():
    owner = uuid4()
    entry = _entry(owner, date(2026, 9, 20))
    outcome = DailyHealthOutcome(user_id=owner, target_date=date(2026, 9, 21),
                                reported_thirst_level_0_10=6, reported_dryness_level_0_10=7)
    # 00:00 on D+1 in Bangkok is 17:00 UTC on D, not UTC midnight.
    cutoff = datetime(2026, 9, 20, 17, tzinfo=UTC)
    def build():
        return build_next_day_training_examples([entry], [outcome], consented_user_ids={owner})
    entry.updated_at = cutoff - timedelta(microseconds=1)
    assert len(build()) == 1
    for stamp in (cutoff, cutoff + timedelta(hours=1), None, cutoff.replace(tzinfo=None)):
        entry.updated_at = stamp
        assert build() == []
    entry.updated_at = cutoff - timedelta(hours=1)
    entry.created_at = cutoff
    assert build() == []
    entry.created_at = None
    assert build() == []


def test_training_examples_require_opted_in_user_and_real_next_day_scores() -> None:
    opted_in_user = uuid4()
    other_user = uuid4()
    prior_date = date(2026, 9, 20)
    target_date = prior_date + timedelta(days=1)
    entries = [
        _entry(opted_in_user, prior_date),
        _entry(other_user, prior_date),
        _entry(opted_in_user, target_date),
    ]
    outcomes = [
        DailyHealthOutcome(
            user_id=opted_in_user,
            target_date=target_date,
            reported_thirst_level_0_10=6.0,
            reported_dryness_level_0_10=7.0,
        ),
        DailyHealthOutcome(
            user_id=other_user,
            target_date=target_date,
            reported_thirst_level_0_10=9.0,
            reported_dryness_level_0_10=9.0,
        ),
    ]

    examples = build_next_day_training_examples(
        entries,
        outcomes,
        consented_user_ids={opted_in_user},
    )

    assert len(examples) == 1
    assert examples[0].participant_id == str(opted_in_user)
    assert examples[0].feature_values == (420.0, 1500.0, 2.0)
    assert examples[0].target_values == (6.0, 7.0)
    assert examples[0].target_date == target_date


def test_next_day_training_does_not_use_predicted_scores_or_missing_prior_day() -> None:
    user_id = uuid4()
    target_date = date(2026, 9, 21)
    only_target_day = _entry(user_id, target_date)
    outcome = DailyHealthOutcome(
        user_id=user_id,
        target_date=target_date,
        reported_thirst_level_0_10=4.0,
        reported_dryness_level_0_10=5.0,
    )

    examples = build_next_day_training_examples(
        [only_target_day],
        [outcome],
        consented_user_ids={user_id},
    )

    assert examples == []


def test_synthetic_source_is_excluded_even_when_real_outcomes_exist() -> None:
    user_id = uuid4()
    prior_date = date(2026, 9, 20)
    synthetic_entry = _entry(user_id, prior_date)
    synthetic_entry.data_source = "synthetic"
    outcome = DailyHealthOutcome(
        user_id=user_id,
        target_date=prior_date + timedelta(days=1),
        reported_thirst_level_0_10=5.0,
        reported_dryness_level_0_10=5.0,
    )

    examples = build_next_day_training_examples(
        [synthetic_entry],
        [outcome],
        consented_user_ids={user_id},
    )

    assert examples == []


def test_participant_split_has_disjoint_train_validation_and_test_groups() -> None:
    examples = []
    for participant in range(5):
        for day in range(3):
            examples.append(
                TrainingExample(
                    participant_id=f"participant-{participant}",
                    target_date=date(2026, 1, 1) + timedelta(days=day),
                    feature_values=(420.0, 1500.0, 2.0),
                    target_values=(5.0, 4.0),
                )
            )

    train, valid, test = split_examples_by_participant(examples)
    groups = [
        {examples[index].participant_id for index in indexes} for indexes in (train, valid, test)
    ]

    assert all(groups)
    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])
    assert sorted(train + valid + test) == list(range(len(examples)))


def test_consent_withdrawal_allows_a_reduced_cohort_candidate() -> None:
    assert should_create_next_candidate(current_records=100, last_candidate_records=120)
    assert should_create_next_candidate(current_records=125, last_candidate_records=100)
    assert not should_create_next_candidate(current_records=124, last_candidate_records=100)


@pytest.mark.asyncio
async def test_energy_loader_requires_expanded_consent_and_honors_withdrawal():
    engine = create_engine("sqlite:///:memory:")
    for table in (
        User.__table__, Consent.__table__, DailyHealthEntry.__table__, DailyHealthOutcome.__table__
    ):
        table.create(engine)
    with SQLSession(engine, expire_on_commit=False) as db:
        old, current = uuid4(), uuid4()
        for user, version in (
            (old, "daily-health-model-training-v1"), (current, "daily-health-model-training-v2")
        ):
            db.add(User(id=user))
            db.add(Consent(user_id=user, version=version))
            db.add(_entry(user, date(2026, 9, 20)))
            db.add(DailyHealthOutcome(user_id=user, target_date=date(2026, 9, 21),
                                     reported_thirst_level_0_10=4, reported_dryness_level_0_10=5,
                                     reported_energy_level_0_10=6))
        db.commit()

        class Adapter:
            async def scalars(self, statement):
                rows = db.scalars(statement).all()
                # SQLite drops timezone metadata; these test-only stamps were stored as UTC.
                # Production PostgreSQL preserves aware timestamps; unknown stamps stay rejected.
                for row in rows:
                    if isinstance(row, DailyHealthEntry):
                        row.created_at = row.created_at.replace(tzinfo=UTC)
                        row.updated_at = row.updated_at.replace(tzinfo=UTC)
                return type("Rows", (), {"all": lambda self: rows})()

        session = Adapter()
        basic = await load_consent_filtered_training_examples(session)
        assert {r.participant_id for r in basic} == {str(old), str(current)}
        energy = await load_consent_filtered_training_examples(session, include_energy=True)
        assert {r.participant_id for r in energy} == {str(current)}
        consent = db.scalar(select(Consent).where(Consent.user_id == current))
        consent.revoked_at = datetime.now(UTC)
        db.commit()
        assert await load_consent_filtered_training_examples(session, include_energy=True) == []
    engine.dispose()
