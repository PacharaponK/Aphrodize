from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from backend.api.schemas.daily_health import DailyHealthOutcomeUpsert
from backend.core.db.models import (
    DailyHealthAgeBand,
    DailyHealthDatasetRecord,
    DailyHealthMenstrualCheckin,
    DailyHealthModelDeployment,
    DailyHealthModelDeploymentEvent,
    DailyHealthModelVersion,
    DailyHealthOutcome,
    DailyHealthProfile,
)


def test_daily_health_collection_tables_are_defined_with_the_documented_keys() -> None:
    assert DailyHealthProfile.__table__.primary_key.columns.keys() == ["user_id"]
    assert DailyHealthAgeBand.__table__.primary_key.columns.keys() == ["user_id"]

    menstrual_uniques = [
        constraint.columns.keys()
        for constraint in DailyHealthMenstrualCheckin.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]
    outcome_uniques = [
        constraint.columns.keys()
        for constraint in DailyHealthOutcome.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]
    dataset_uniques = [
        constraint.columns.keys()
        for constraint in DailyHealthDatasetRecord.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]
    assert ["user_id", "local_date"] in menstrual_uniques
    assert ["user_id", "target_date"] in outcome_uniques
    assert ["dataset_fingerprint", "source_row_number"] in dataset_uniques


def test_observed_outcome_contract_rejects_invalid_scores() -> None:
    with pytest.raises(ValidationError):
        DailyHealthOutcomeUpsert(
            target_date=date(2026, 9, 27), reported_dryness_level_0_10=10.1
        )


def test_model_deployment_keeps_version_foreign_keys_but_audit_event_does_not() -> None:
    deployment_sql = str(CreateTable(DailyHealthModelDeployment.__table__).compile(
        dialect=postgresql.dialect()
    ))
    event_sql = str(CreateTable(DailyHealthModelDeploymentEvent.__table__).compile(
        dialect=postgresql.dialect()
    ))
    version_sql = str(CreateTable(DailyHealthModelVersion.__table__).compile(
        dialect=postgresql.dialect()
    ))

    assert deployment_sql.count("REFERENCES daily_health_model_versions") == 2
    assert "REFERENCES daily_health_model_versions" not in event_sql
    assert "UNIQUE (dataset_fingerprint)" in version_sql
