"""Idempotent import helpers for archived daily-health CSV datasets."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.db.models import DailyHealthDatasetRecord

REQUIRED_COLUMNS = {"local_date", "data_origin", "generation_rule_version"}
USER_ID_COLUMNS = {"user_id", "source_user_id"}
ALLOWED_COLUMNS = {
    "user_id",
    "local_date",
    "timezone",
    "baseline_skin_type",
    "sleep_record_status",
    "sleep_duration_hours",
    "sleep_duration_mins",
    "sleep_duration_total_minutes",
    "water_intake_ml",
    "thirst_score_0_10",
    "outdoor_exposure_choice",
    "outdoor_exposure_band",
    "outdoor_minutes_estimate",
    "skin_dryness_score_0_10",
    "data_origin",
    "generation_rule_version",
    "source_user_id",
    "source_local_date_raw",
    "source_sleep_duration_hours_raw",
    "source_sleep_duration_mins_raw",
    "skin_dryness_level",
    "skin_feeling_status",
    "outdoor_minutes",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def parse_daily_health_dataset_csv(
    contents: bytes,
    *,
    source_dataset_name: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Normalize an imported CSV while preserving provenance and excluding every row from training.

    Participant identifiers are replaced with dataset-local aliases before persistence. Imported
    synthetic targets and categorical historical skin observations are not treated as score labels.
    """
    fingerprint = hashlib.sha256(contents).hexdigest()
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Dataset must be a UTF-8 CSV file") from error

    reader = csv.DictReader(io.StringIO(text))
    columns = set(reader.fieldnames or ())
    if len(columns) != len(reader.fieldnames or ()):
        raise ValueError("Dataset contains duplicate column names")
    unexpected = columns - ALLOWED_COLUMNS
    if unexpected:
        raise ValueError(f"Dataset contains unapproved columns: {', '.join(sorted(unexpected))}")
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")

    rows: list[dict[str, Any]] = []
    participant_aliases: dict[str, str] = {}
    for row_number, source_row in enumerate(reader, start=1):
        if not source_row:
            continue
        if None in source_row:
            raise ValueError(f"Dataset row {row_number} has more cells than approved columns")

        participant_identity = (
            source_row.get("user_id", "").strip() or source_row.get("source_user_id", "").strip()
        )
        participant_key = None
        if participant_identity:
            participant_key = participant_aliases.setdefault(
                participant_identity,
                f"participant_{len(participant_aliases) + 1:04d}",
            )

        data_origin = (source_row.get("data_origin") or "").strip()
        if data_origin == "real_user_tracker_xlsx":
            data_source = "observed"
            exclusion_reason = "imported_labels_not_numeric_ground_truth"
        elif data_origin.startswith("sandbox_synthetic_"):
            data_source = "synthetic"
            exclusion_reason = "synthetic_labels_are_not_observed_outcomes"
        else:
            data_source = "unknown"
            exclusion_reason = "unrecognized_dataset_provenance"

        raw_date = (source_row.get("local_date") or "").strip()
        try:
            local_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError as error:
            raise ValueError(f"Invalid local_date on dataset row {row_number}") from error

        payload: dict[str, str | None] = {
            column: (value.strip() or None) if value is not None else None
            for column, value in source_row.items()
            if column is not None
        }
        for identifier_column in USER_ID_COLUMNS:
            if identifier_column in payload:
                payload[identifier_column] = participant_key
        payload["participant_key"] = participant_key

        rows.append(
            {
                "dataset_fingerprint": fingerprint,
                "source_dataset_name": Path(source_dataset_name).name[:255],
                "source_row_number": row_number,
                "participant_key": participant_key,
                "local_date": local_date,
                "data_source": data_source,
                "generation_rule_version": (
                    source_row.get("generation_rule_version", "").strip() or None
                ),
                "training_eligible": False,
                "training_exclusion_reason": exclusion_reason,
                "record_payload": payload,
            }
        )

    if not rows:
        raise ValueError("Dataset contains no data rows")
    return fingerprint, rows


async def delete_daily_health_dataset_snapshot(
    session: AsyncSession,
    fingerprint: str,
) -> int:
    """Delete every archived row from one explicitly identified imported CSV snapshot."""
    if not SHA256_PATTERN.fullmatch(fingerprint):
        raise ValueError("A 64-character SHA-256 fingerprint is required")
    result = await session.execute(
        delete(DailyHealthDatasetRecord).where(
            DailyHealthDatasetRecord.dataset_fingerprint == fingerprint
        )
    )
    await session.commit()
    return result.rowcount or 0


async def import_daily_health_dataset(
    session: AsyncSession,
    *,
    dataset_path: Path,
) -> dict[str, int | str]:
    """Persist a CSV snapshot once; repeated imports of the same file are no-ops."""
    contents = dataset_path.read_bytes()
    fingerprint, rows = parse_daily_health_dataset_csv(
        contents,
        source_dataset_name=dataset_path.name,
    )
    statement = insert(DailyHealthDatasetRecord).values(rows)
    statement = statement.on_conflict_do_nothing(
        index_elements=[
            DailyHealthDatasetRecord.dataset_fingerprint,
            DailyHealthDatasetRecord.source_row_number,
        ]
    )
    result = await session.execute(statement)
    await session.commit()
    return {
        "dataset_fingerprint": fingerprint,
        "rows_read": len(rows),
        "rows_inserted": result.rowcount or 0,
    }
