from datetime import date, timedelta
from uuid import uuid4

from backend.core.db.models import DailyHealthEntry, DailyHealthOutcome
from backend.services.daily_health_training import (
    TrainingExample,
    build_next_day_training_examples,
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
    )


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
