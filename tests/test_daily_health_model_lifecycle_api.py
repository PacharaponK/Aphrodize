from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from backend.api.schemas.daily_health import (
    DailyHealthModelPromotionRequest,
    DailyHealthModelRollbackRequest,
    DailyHealthPredictionRequest,
)
from backend.api.v1.routes import daily_health
from backend.core.db.models import (
    DailyHealthModelDeployment,
    DailyHealthModelDeploymentEvent,
    DailyHealthModelVersion,
    User,
)


class Rows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, *, versions=None, deployment=None, has_training_data=True):
        self.versions = versions or []
        self.deployment = deployment
        self.has_training_data = has_training_data
        self.statements = []
        self.added = []
        self.committed = False

    async def get(self, model, key):
        if model is User:
            return object()
        if model is DailyHealthModelDeployment:
            return self.deployment
        if model is DailyHealthModelVersion:
            return next((version for version in self.versions if version.version_id == key), None)
        return None

    async def scalars(self, _statement):
        return Rows(self.versions)

    async def scalar(self, _statement):
        return uuid4() if self.has_training_data else None

    async def execute(self, statement):
        self.statements.append(statement)
        return SimpleNamespace(rowcount=0)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True


def make_version(version_id: str):
    return SimpleNamespace(version_id=version_id, status="candidate")


@pytest.mark.asyncio
async def test_live_prediction_route_passes_active_candidate_bundle_to_inference(
    monkeypatch,
) -> None:
    bundle = {
        "model": object(),
        "metadata": {"model_id": "daily-health-next-day-0123456789abcdef"},
    }

    class Predictor:
        class ScoreModelUnavailable(RuntimeError):
            pass

        def predict_daily_health(self, **kwargs):
            return kwargs["model_bundle"]

    async def active_bundle(_session):
        return bundle

    monkeypatch.setattr(daily_health, "get_daily_score_model", lambda: Predictor())
    monkeypatch.setattr(daily_health, "get_serving_daily_health_bundle", active_bundle)
    payload = DailyHealthPredictionRequest(
        local_date="2026-09-26",
        sleep_hours=7,
        sleep_minutes=20,
        water_intake_ml=1400,
        outdoor_exposure_choice=2,
    )

    result = await daily_health._run_daily_health_prediction(
        payload,
        session=object(),
        allow_out_of_domain_test_prediction=False,
    )

    assert result is bundle


@pytest.mark.asyncio
async def test_candidate_promotion_requires_review_and_records_audit_event(monkeypatch) -> None:
    version_id = "daily-health-next-day-0123456789abcdef"
    session = FakeSession(versions=[make_version(version_id)])
    monkeypatch.setattr(daily_health, "load_approved_candidate_bundle", lambda _version: {})

    result = await daily_health.promote_daily_health_model(
        DailyHealthModelPromotionRequest(
            version_id=version_id,
            approval_reason="Reviewed holdout and approved for a monitored trial",
        ),
        session,
    )

    deployment = next(
        item for item in session.added if isinstance(item, DailyHealthModelDeployment)
    )
    event = next(
        item for item in session.added if isinstance(item, DailyHealthModelDeploymentEvent)
    )
    assert result["active_version_id"] == version_id
    assert deployment.active_version_id == version_id
    assert event.action == "promote"
    assert event.reason.startswith("Reviewed holdout")
    assert session.committed is True


@pytest.mark.asyncio
async def test_candidate_promotion_refuses_an_invalid_artifact(monkeypatch) -> None:
    version_id = "daily-health-next-day-0123456789abcdef"
    session = FakeSession(versions=[make_version(version_id)])

    def invalid(_version):
        raise daily_health.DailyHealthCandidateUnavailable("invalid")

    monkeypatch.setattr(daily_health, "load_approved_candidate_bundle", invalid)
    with pytest.raises(HTTPException) as error:
        await daily_health.promote_daily_health_model(
            DailyHealthModelPromotionRequest(
                version_id=version_id,
                approval_reason="Reviewed this candidate and checked holdout metrics",
            ),
            session,
        )

    assert error.value.status_code == 409
    assert not session.committed


@pytest.mark.asyncio
async def test_rollback_swaps_to_previous_approved_candidate_and_is_audited(monkeypatch) -> None:
    active_id = "daily-health-next-day-aaaaaaaaaaaaaaaa"
    previous_id = "daily-health-next-day-bbbbbbbbbbbbbbbb"
    active = make_version(active_id)
    previous = make_version(previous_id)
    deployment = DailyHealthModelDeployment(
        deployment_key="daily_health",
        active_version_id=active_id,
        previous_version_id=previous_id,
        approval_reason="Initial review",
    )
    session = FakeSession(versions=[active, previous], deployment=deployment)
    monkeypatch.setattr(daily_health, "load_approved_candidate_bundle", lambda _version: {})

    result = await daily_health.rollback_daily_health_model(
        DailyHealthModelRollbackRequest(reason="Rollback after a regression was observed"),
        session,
    )

    assert result["active_version_id"] == previous_id
    assert result["previous_version_id"] == active_id
    assert any(
        isinstance(item, DailyHealthModelDeploymentEvent) and item.action == "rollback"
        for item in session.added
    )
    assert session.committed is True


@pytest.mark.asyncio
async def test_withdrawing_training_consent_does_not_stale_the_active_model() -> None:
    active_id = "daily-health-next-day-0123456789abcdef"
    deployment = DailyHealthModelDeployment(
        deployment_key="daily_health",
        active_version_id=active_id,
        previous_version_id=None,
        approval_reason="Approved candidate",
    )
    session = FakeSession(deployment=deployment)

    await daily_health.revoke_daily_health_model_training_consent(uuid4(), session)

    model_update = next(
        statement
        for statement in session.statements
        if "daily_health_model_versions" in str(statement).lower()
    )
    compiled = model_update.compile(dialect=postgresql.dialect())
    assert "version_id !=" in str(compiled)
    assert active_id in compiled.params.values()
    assert session.committed is True


@pytest.mark.asyncio
async def test_user_data_erasure_removes_history_invalidates_deployment_and_purges_candidates(
    monkeypatch,
) -> None:
    version_id = "daily-health-next-day-0123456789abcdef"
    deployment = DailyHealthModelDeployment(
        deployment_key="daily_health",
        active_version_id=version_id,
        previous_version_id=None,
        approval_reason="Approved candidate",
    )
    session = FakeSession(versions=[make_version(version_id)], deployment=deployment)
    purged = []
    monkeypatch.setattr(
        daily_health,
        "purge_generated_candidate_artifacts",
        lambda ids: purged.extend(ids),
    )

    await daily_health.delete_daily_health_data(uuid4(), session)

    statements = [
        str(item.compile(dialect=postgresql.dialect())).upper() for item in session.statements
    ]
    for table in (
        "DAILY_HEALTH_OUTCOMES",
        "DAILY_HEALTH_ENTRIES",
        "DAILY_HEALTH_MENSTRUAL_CHECKINS",
        "DAILY_HEALTH_AGE_BANDS",
        "DAILY_HEALTH_PROFILES",
    ):
        assert any(f"DELETE FROM {table}" in statement for statement in statements)
    assert any("UPDATE CONSENTS" in statement for statement in statements)
    assert any("DELETE FROM DAILY_HEALTH_MODEL_VERSIONS" in statement for statement in statements)
    assert any(
        "DELETE FROM DAILY_HEALTH_MODEL_DEPLOYMENT_EVENTS" in statement for statement in statements
    )
    assert deployment.active_version_id is None
    assert deployment.previous_version_id is None
    assert purged == [version_id]
    assert any(isinstance(item, DailyHealthModelDeploymentEvent) for item in session.added)


@pytest.mark.asyncio
async def test_non_contributor_cannot_reset_shared_candidate_registry(monkeypatch) -> None:
    version_id = "daily-health-next-day-0123456789abcdef"
    deployment = DailyHealthModelDeployment(
        deployment_key="daily_health",
        active_version_id=version_id,
    )
    session = FakeSession(
        versions=[make_version(version_id)],
        deployment=deployment,
        has_training_data=False,
    )
    purged = []
    monkeypatch.setattr(daily_health, "purge_generated_candidate_artifacts", purged.append)

    await daily_health.delete_daily_health_data(uuid4(), session)

    statements = [str(item).upper() for item in session.statements]
    assert not any("DELETE FROM DAILY_HEALTH_MODEL_VERSIONS" in item for item in statements)
    assert deployment.active_version_id == version_id
    assert purged == []
    assert session.committed is True
    assert session.committed is True
