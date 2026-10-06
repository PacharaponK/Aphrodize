"""Consent-filtered next-day candidate training and immutable model versioning."""

from __future__ import annotations

import hashlib
import json
import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.consents import MODEL_TRAINING_CONSENT_VERSION, MODEL_TRAINING_CONSENT_VERSIONS
from backend.core.db.models import (
    Consent,
    DailyHealthEntry,
    DailyHealthModelVersion,
    DailyHealthOutcome,
)

logger = logging.getLogger(__name__)
MIN_TRAINING_RECORDS = 100
MIN_TRAINING_PARTICIPANTS = 5
MIN_NEW_RECORDS_PER_VERSION = 25
MODEL_FAMILY = "daily_health_next_day_random_forest"
FEATURE_NAMES = ["sleep_duration_minutes", "water_intake_ml", "outdoor_exposure_choice"]
TARGET_NAMES = ["reported_thirst_level_0_10", "reported_dryness_level_0_10"]
ENERGY_TARGET_NAMES = [*TARGET_NAMES, "reported_energy_level_0_10"]
FEATURE_AVAILABILITY_POLICY = "created-and-updated-before-target-bangkok-day-v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = (
    REPOSITORY_ROOT
    / "models"
    / "time-series"
    / "non-linear-model"
    / "artifacts"
    / "user-candidates"
)


@dataclass(frozen=True, slots=True)
class TrainingExample:
    participant_id: str
    target_date: date
    feature_values: tuple[float, float, float]
    target_values: tuple[float, ...]


def inputs_available_before_target(entry: DailyHealthEntry, target_date: date) -> bool:
    """Mutable records have no historical snapshot: reject late or unprovable inputs."""
    cutoff = datetime.combine(target_date, datetime.min.time(), ZoneInfo("Asia/Bangkok"))
    created, updated = entry.created_at, entry.updated_at
    return (
        isinstance(created, datetime) and created.utcoffset() is not None
        and isinstance(updated, datetime) and updated.utcoffset() is not None
        and created <= updated < cutoff
    )


def build_next_day_training_examples(
    entries: Sequence[DailyHealthEntry],
    outcomes: Sequence[DailyHealthOutcome],
    *,
    consented_user_ids: set[UUID],
    include_energy: bool = False,
) -> list[TrainingExample]:
    """Pair a self-reported day's outcomes with the opted-in user's previous-day inputs."""
    entries_by_user_date: dict[tuple[UUID, date], DailyHealthEntry] = {}
    for entry in entries:
        if entry.data_source == "user_reported":
            entries_by_user_date[(entry.user_id, entry.local_date)] = entry

    examples: list[TrainingExample] = []
    for outcome in outcomes:
        user_id = outcome.user_id
        thirst = outcome.reported_thirst_level_0_10
        dryness = outcome.reported_dryness_level_0_10
        if user_id not in consented_user_ids or thirst is None or dryness is None:
            continue
        energy = outcome.reported_energy_level_0_10
        if include_energy and energy is None:
            continue

        prior_day = outcome.target_date - timedelta(days=1)
        entry = entries_by_user_date.get((user_id, prior_day))
        if entry is None or not inputs_available_before_target(entry, outcome.target_date):
            continue

        examples.append(
            TrainingExample(
                participant_id=str(user_id),
                target_date=outcome.target_date,
                feature_values=(
                    float(entry.sleep_duration_minutes),
                    float(entry.water_intake_ml),
                    float(entry.outdoor_exposure_choice),
                ),
                target_values=(float(thirst), float(dryness), float(energy))
                if include_energy else (float(thirst), float(dryness)),
            )
        )
    return sorted(examples, key=lambda item: (item.target_date, item.participant_id))


def split_examples_by_participant(
    examples: Sequence[TrainingExample],
) -> tuple[list[int], list[int], list[int]]:
    """Return deterministic train/validation/test indexes with no participant overlap."""
    participants = sorted({example.participant_id for example in examples})
    if len(participants) < MIN_TRAINING_PARTICIPANTS:
        raise ValueError(f"At least {MIN_TRAINING_PARTICIPANTS} opted-in participants are required")

    random.Random(42).shuffle(participants)
    test_count = max(1, round(len(participants) * 0.2))
    validation_count = max(1, round(len(participants) * 0.2))
    test_participants = set(participants[:test_count])
    validation_participants = set(participants[test_count : test_count + validation_count])
    train_participants = set(participants[test_count + validation_count :])

    train = [
        i for i, example in enumerate(examples) if example.participant_id in train_participants
    ]
    valid = [
        i for i, example in enumerate(examples) if example.participant_id in validation_participants
    ]
    test = [i for i, example in enumerate(examples) if example.participant_id in test_participants]
    if not train or not valid or not test:
        raise ValueError("The user-level dataset split produced an empty partition")
    return train, valid, test


def training_dataset_fingerprint(examples: Sequence[TrainingExample]) -> str:
    """Hash the opted-in training snapshot without writing participant IDs to the registry."""
    aliases = {
        participant_id: f"participant_{index:04d}"
        for index, participant_id in enumerate(
            sorted({example.participant_id for example in examples}),
            start=1,
        )
    }
    payload = [
        {
            "participant": aliases[example.participant_id],
            "target_date": example.target_date.isoformat(),
            "features": example.feature_values,
            "targets": example.target_values,
        }
        for example in examples
    ]
    canonical = json.dumps(
        {"feature_availability_policy": FEATURE_AVAILABILITY_POLICY,
         "training_consent_policy": MODEL_TRAINING_CONSENT_VERSION,
         "examples": payload}, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def should_create_next_candidate(
    *, current_records: int, last_candidate_records: int | None
) -> bool:
    if last_candidate_records is None or current_records < last_candidate_records:
        return True
    return current_records - last_candidate_records >= MIN_NEW_RECORDS_PER_VERSION


async def load_consent_filtered_training_examples(
    session: AsyncSession,
    *, include_energy: bool = False,
) -> list[TrainingExample]:
    consented_result = await session.scalars(
        select(Consent.user_id).where(
            Consent.version.in_(
                (MODEL_TRAINING_CONSENT_VERSION,) if include_energy
                else MODEL_TRAINING_CONSENT_VERSIONS
            ),
            Consent.revoked_at.is_(None),
        )
    )
    consented_user_ids = set(consented_result.all())
    if not consented_user_ids:
        return []

    entries_result = await session.scalars(
        select(DailyHealthEntry).where(
            DailyHealthEntry.user_id.in_(consented_user_ids),
            DailyHealthEntry.data_source == "user_reported",
        ).execution_options(populate_existing=True)
    )
    outcomes_result = await session.scalars(
        select(DailyHealthOutcome).where(
            DailyHealthOutcome.user_id.in_(consented_user_ids),
            DailyHealthOutcome.reported_thirst_level_0_10.is_not(None),
            DailyHealthOutcome.reported_dryness_level_0_10.is_not(None),
        ).execution_options(populate_existing=True)
    )
    return build_next_day_training_examples(
        list(entries_result.all()),
        list(outcomes_result.all()),
        consented_user_ids=consented_user_ids,
        include_energy=include_energy,
    )


async def load_preferred_training_examples(
    session: AsyncSession,
) -> tuple[list[TrainingExample], list[str]]:
    """Prefer three real targets only when their own cohort meets the existing floor."""
    extended = await load_consent_filtered_training_examples(session, include_energy=True)
    if (len(extended) >= MIN_TRAINING_RECORDS
            and len({row.participant_id for row in extended}) >= MIN_TRAINING_PARTICIPANTS):
        return extended, ENERGY_TARGET_NAMES
    return await load_consent_filtered_training_examples(session), TARGET_NAMES


async def enqueue_candidate_training_if_ready(session: AsyncSession) -> bool:
    """Queue at most one daily training attempt, without failing a saved outcome."""
    examples, target_names = await load_preferred_training_examples(session)
    participant_count = len({example.participant_id for example in examples})
    if len(examples) < MIN_TRAINING_RECORDS or participant_count < MIN_TRAINING_PARTICIPANTS:
        return False

    fingerprint = training_dataset_fingerprint(examples)
    existing_result = await session.scalars(
        select(DailyHealthModelVersion.version_id).where(
            DailyHealthModelVersion.dataset_fingerprint == fingerprint,
            DailyHealthModelVersion.status.in_(["training", "candidate"]),
        )
    )
    if existing_result.first() is not None:
        return False

    latest_candidate = await session.scalar(
        select(DailyHealthModelVersion)
        .where(DailyHealthModelVersion.status == "candidate")
        .order_by(DailyHealthModelVersion.created_at.desc())
        .limit(1)
    )
    if not should_create_next_candidate(
        current_records=len(examples),
        last_candidate_records=(
            latest_candidate.training_records
            if latest_candidate is not None
            and ("reported_energy_level_0_10" in (latest_candidate.metrics or {}).get("test", {}))
            == (target_names == ENERGY_TARGET_NAMES)
            else None
        ),
    ):
        return False

    from backend.libs.redis_client import get_arq_pool

    redis = await get_arq_pool()
    try:
        job = await redis.enqueue_job(
            "run_daily_health_candidate_training",
            _queue_name="training",
            _job_id=f"daily-health-candidate-{fingerprint[:24]}",
        )
        return job is not None
    finally:
        await redis.close()


def _split_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, target_names: list[str] = TARGET_NAMES,
) -> dict[str, dict[str, float | None]]:
    metrics: dict[str, dict[str, float | None]] = {}
    for index, target_name in enumerate(target_names):
        actual = y_true[:, index]
        predicted = y_pred[:, index]
        r2 = None
        if len(actual) >= 2 and len(np.unique(actual)) > 1:
            r2 = float(r2_score(actual, predicted))
        metrics[target_name] = {
            "mae": float(mean_absolute_error(actual, predicted)),
            "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
            "r2": r2,
        }
    return metrics


async def train_daily_health_candidate(session: AsyncSession) -> DailyHealthModelVersion | None:
    """Train and persist a review-only candidate; the production predictor is not changed."""
    examples, target_names = await load_preferred_training_examples(session)
    participants = {example.participant_id for example in examples}
    if len(examples) < MIN_TRAINING_RECORDS or len(participants) < MIN_TRAINING_PARTICIPANTS:
        return None

    fingerprint = training_dataset_fingerprint(examples)
    existing = await session.scalar(
        select(DailyHealthModelVersion).where(
            DailyHealthModelVersion.dataset_fingerprint == fingerprint
        )
    )
    if existing is not None and existing.status in {"training", "candidate"}:
        return existing

    version_id = f"daily-health-next-day-{fingerprint[:16]}"
    if existing is None:
        version = DailyHealthModelVersion(
            version_id=version_id,
            model_family=MODEL_FAMILY,
            status="training",
            dataset_fingerprint=fingerprint,
            training_records=len(examples),
            participant_count=len(participants),
        )
        session.add(version)
    else:
        version = existing
        version.status = "training"
        version.training_records = len(examples)
        version.participant_count = len(participants)
        version.metrics = None
        version.artifact_uri = None
        version.mlflow_run_id = None
    await session.commit()

    try:
        x = np.asarray([example.feature_values for example in examples], dtype=float)
        y = np.asarray([example.target_values for example in examples], dtype=float)
        train_indexes, validation_indexes, test_indexes = split_examples_by_participant(examples)
        model = RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(x[train_indexes], y[train_indexes])
        validation_metrics = _split_metrics(
            y[validation_indexes], model.predict(x[validation_indexes]), target_names
        )
        test_metrics = _split_metrics(y[test_indexes], model.predict(x[test_indexes]), target_names)
        test_baseline = _split_metrics(
            y[test_indexes],
            np.tile(np.mean(y[train_indexes], axis=0), (len(test_indexes), 1)), target_names,
        )
        # Chronological validation: train only on dates before the temporal holdout.
        dates = sorted({row.target_date for row in examples})
        cutoff = dates[max(1, int(len(dates) * 0.8))] if len(dates) >= 5 else None
        temporal_metrics = None
        temporal_baseline = None
        if cutoff is not None:
            earlier = [i for i, row in enumerate(examples) if row.target_date < cutoff]
            later = [i for i, row in enumerate(examples) if row.target_date >= cutoff]
            temporal_model = RandomForestRegressor(
                n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1,
            ).fit(x[earlier], y[earlier])
            temporal_metrics = _split_metrics(
                y[later], temporal_model.predict(x[later]), target_names,
            )
            temporal_baseline = _split_metrics(
                y[later], np.tile(np.mean(y[earlier], axis=0), (len(later), 1)), target_names,
            )

        current_status = await session.scalar(
            select(DailyHealthModelVersion.status)
            .where(DailyHealthModelVersion.version_id == version_id)
            .with_for_update()
        )
        if current_status == "stale":
            version.status = "stale"
            await session.commit()
            return version
        current_examples = await load_consent_filtered_training_examples(
            session, include_energy=target_names == ENERGY_TARGET_NAMES,
        )
        if training_dataset_fingerprint(current_examples) != fingerprint:
            version.status = "stale"
            await session.commit()
            return version

        artifact_dir = ARTIFACT_ROOT / version_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        model_path = artifact_dir / "model.joblib"
        joblib.dump(model, model_path)
        artifact_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
        manifest = {
            "version_id": version_id,
            "model_family": MODEL_FAMILY,
            "model_type": "RandomForestRegressor",
            "prediction_horizon_days": 1,
            "features": FEATURE_NAMES,
            "targets": target_names,
            "training_records": len(examples),
            "participant_count": len(participants),
            "dataset_fingerprint": fingerprint,
            "artifact_sha256": artifact_sha256,
            "data_policy": "active_opt_in_and_user_reported_numeric_outcomes_only",
            "synthetic_data_included": False,
            "predictions_used_as_labels": False,
            "feature_availability_policy": FEATURE_AVAILABILITY_POLICY,
            "training_consent_versions": (
                [MODEL_TRAINING_CONSENT_VERSION] if target_names == ENERGY_TARGET_NAMES
                else list(MODEL_TRAINING_CONSENT_VERSIONS)
            ),
            "split_policy": "participant_group_holdout_60_20_20",
            "metrics": {
                "validation": validation_metrics, "test": test_metrics,
                "test_mean_baseline": test_baseline,
                "temporal_test": temporal_metrics, "temporal_mean_baseline": temporal_baseline,
            },
            "trained_at": datetime.now(UTC).isoformat(),
        }
        (artifact_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False),
            encoding="utf-8",
        )

        version.status = "candidate"
        version.metrics = manifest["metrics"]
        version.artifact_uri = str(model_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
        version.completed_at = datetime.now(UTC)
        await session.commit()
        return version
    except Exception:
        version.status = "failed"
        await session.commit()
        logger.exception("Daily-health candidate training failed")
        raise
