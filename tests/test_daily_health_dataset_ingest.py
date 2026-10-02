from datetime import date

import pytest

from backend.services.daily_health_dataset import (
    delete_daily_health_dataset_snapshot,
    parse_daily_health_dataset_csv,
)


def test_dataset_import_preserves_provenance_without_treating_synthetic_scores_as_truth() -> None:
    dataset = (
        b"user_id,local_date,timezone,thirst_score_0_10,skin_dryness_score_0_10,"
        b"skin_dryness_level,data_origin,generation_rule_version,source_user_id\n"
        b"private-user,2026-09-12,Asia/Bangkok,,,0.3,real_user_tracker_xlsx,,private-user\n"
        b"synthetic_user_01,2026-08-01,Asia/Bangkok,5.2,7.1,,"
        b"sandbox_synthetic_medical_cautious,forecast_v2,seed-user\n"
    )

    fingerprint, rows = parse_daily_health_dataset_csv(
        dataset,
        source_dataset_name="daily_health.csv",
    )

    assert len(fingerprint) == 64
    assert len(rows) == 2
    assert rows[0]["data_source"] == "observed"
    assert rows[0]["local_date"] == date(2026, 9, 12)
    assert rows[0]["training_eligible"] is False
    assert rows[0]["record_payload"]["skin_dryness_level"] == "0.3"
    assert rows[0]["record_payload"]["thirst_score_0_10"] is None
    assert "private-user" not in str(rows[0]["record_payload"])

    assert rows[1]["data_source"] == "synthetic"
    assert rows[1]["training_eligible"] is False
    assert rows[1]["record_payload"]["thirst_score_0_10"] == "5.2"
    assert rows[1]["training_exclusion_reason"] == "synthetic_labels_are_not_observed_outcomes"


def test_dataset_import_rejects_unrecognized_columns_instead_of_archiving_unreviewed_fields() -> (
    None
):
    dataset = (
        b"user_id,local_date,data_origin,generation_rule_version,email\n"
        b"private-user,2026-09-12,real_user_tracker_xlsx,,person@example.com\n"
    )

    try:
        parse_daily_health_dataset_csv(dataset, source_dataset_name="daily_health.csv")
    except ValueError as error:
        assert "email" in str(error)
    else:
        raise AssertionError("unreviewed CSV columns must not be persisted")


@pytest.mark.asyncio
async def test_snapshot_delete_requires_sha256_and_deletes_only_matching_imported_rows() -> None:
    class Result:
        rowcount = 17

    class Session:
        def __init__(self) -> None:
            self.statement = None
            self.committed = False

        async def execute(self, statement):
            self.statement = statement
            return Result()

        async def commit(self):
            self.committed = True

    session = Session()
    deleted = await delete_daily_health_dataset_snapshot(session, "a" * 64)

    assert deleted == 17
    assert "dataset_fingerprint" in str(session.statement)
    assert session.committed is True


@pytest.mark.asyncio
async def test_snapshot_delete_rejects_invalid_fingerprint_before_database_write() -> None:
    class Session:
        async def execute(self, _statement):
            raise AssertionError("invalid fingerprint must not reach the database")

    with pytest.raises(ValueError, match="64-character SHA-256"):
        await delete_daily_health_dataset_snapshot(Session(), "not-a-fingerprint")
