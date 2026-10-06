from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SQLSession

from backend.api.deps import require_user_token
from backend.api.schemas.acne import AcneConsentInput, AcneInput, AcneTrainingConsentInput
from backend.api.v1.routes import acne
from backend.core.consents import (
    ACNE_MODEL_TRAINING_CONSENT_VERSION,
    MODEL_TRAINING_CONSENT_VERSION,
)
from backend.core.db.models import AcneObservation, Consent, DailyHealthEntry, User
from backend.core.db.session import get_session


class Session:
    def __init__(self, user_id, consent=False):
        self.user_id = user_id
        self.consent = consent
        self.row = None
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        if "FROM users" in str(statement):
            return User(id=self.user_id, status="active")
        if "FROM consents" in str(statement):
            return uuid4() if self.consent else None
        return self.row

    async def scalars(self, statement):
        self.statements.append(statement)
        rows = [self.row] if self.row else []
        return type("Rows", (), {"all": lambda self: rows})()

    def add(self, row):
        if isinstance(row, Consent):
            self.consent = True
        else:
            self.row = row

    async def commit(self):
        pass

    async def refresh(self, row):
        row.updated_at = datetime.now(UTC)

    async def execute(self, statement):
        self.statements.append(statement)


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(acne.settings, "acne_tracking_enabled", True)


def test_schema_distinguishes_no_unsure_and_rejects_invalid_regions():
    assert AcneInput(local_date="2026-01-01", response="unsure").response == "unsure"
    assert AcneInput(local_date="2026-01-01", response="no").regions == []
    for payload in [
        {"response": "no", "regions": ["chin"]},
        {"response": "yes", "regions": ["chin", "chin"]},
        {"response": "yes", "regions": ["unknown"]},
        {"response": "yes", "user_id": str(uuid4())},
    ]:
        with pytest.raises(ValidationError):
            AcneInput(local_date="2026-01-01", **payload)
    with pytest.raises(ValidationError):
        AcneConsentInput(consent_to_store=False)


@pytest.mark.asyncio
async def test_save_requires_independent_consent_and_rejects_future(enabled):
    user = uuid4()
    session = Session(user)
    payload = AcneInput(local_date="2026-01-01", response="yes")
    with pytest.raises(HTTPException) as error:
        await acne.save(user, payload, session)
    assert error.value.status_code == 403
    future = AcneInput(local_date=date.today() + timedelta(days=3), response="no")
    with pytest.raises(HTTPException) as error:
        await acne.save(user, future, session)
    assert error.value.status_code == 422
    assert session.row is None


@pytest.mark.asyncio
async def test_save_update_and_history_keep_observed_provenance(enabled):
    user = uuid4()
    session = Session(user)
    await acne.grant(user, AcneConsentInput(consent_to_store=True), session)
    first = await acne.save(
        user, AcneInput(local_date="2026-01-01", response="yes", regions=["chin"]), session
    )
    assert first.provenance == "user_reported"
    assert first.consent_version == acne.VERSION
    second = await acne.save(user, AcneInput(local_date="2026-01-01", response="unsure"), session)
    assert second.response == "unsure" and second.regions == []
    history = await acne.history(user, 30, session)
    assert history["items"][0]["response"] == "unsure"
    assert "user_id" not in history["items"][0]
    query = session.statements[-1]
    assert user in query.compile().params.values()


@pytest.mark.asyncio
async def test_withdraw_and_delete_only_touch_owner_acne_scope(enabled):
    user = uuid4()
    session = Session(user, consent=True)
    await acne.withdraw(user, session)
    update, deletion = session.statements[-2:]
    assert set(update.compile().params["version_1"]) == {
        acne.VERSION,
        ACNE_MODEL_TRAINING_CONSENT_VERSION,
    }
    assert user in deletion.compile().params.values()
    assert "DELETE FROM acne_observations" in str(deletion)
    assert "daily_health" not in str(deletion)
    await acne.remove(user, date(2026, 1, 1), session)
    assert date(2026, 1, 1) in session.statements[-1].compile().params.values()


@pytest.mark.asyncio
async def test_disabled_does_not_expose_reports_or_collect(monkeypatch):
    monkeypatch.setattr(acne.settings, "acne_tracking_enabled", False)
    user = uuid4()
    session = Session(user, consent=True)
    assert await acne.history(user, 30, session) == {
        "enabled": False,
        "consent_active": False,
        "items": [],
    }
    with pytest.raises(HTTPException) as error:
        await acne.grant(user, AcneConsentInput(consent_to_store=True), session)
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_http_cross_account_rejected_and_owner_response_not_cached(enabled):
    user = uuid4()
    session = Session(user)
    app = FastAPI()
    app.include_router(acne.router, prefix="/acne")
    app.dependency_overrides[require_user_token] = lambda: user
    app.dependency_overrides[get_session] = lambda: session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        denied = await client.get(f"/acne/users/{uuid4()}")
        assert denied.status_code == 403
        assert session.statements == []
        denied_training = await client.put(
            f"/acne/users/{uuid4()}/training-consent", json={"consent_to_train_acne": True}
        )
        assert denied_training.status_code == 403
        assert session.statements == []
        response = await client.get(f"/acne/users/{user}")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert "readiness" not in response.json()


def test_new_table_has_owner_date_and_response_constraints():
    names = {constraint.name for constraint in AcneObservation.__table__.constraints}
    assert "uq_acne_observation_user_date" in names
    assert "ck_acne_response" in names


@pytest.mark.asyncio
async def test_real_database_crud_withdrawal_isolation(enabled):
    engine = create_engine("sqlite:///:memory:")
    for table in (User.__table__, Consent.__table__, AcneObservation.__table__):
        table.create(engine)
    with SQLSession(engine, expire_on_commit=False) as database:
        first, second = uuid4(), uuid4()
        database.add_all([User(id=first), User(id=second)])
        database.commit()

        class Adapter:
            async def scalar(self, statement):
                return database.scalar(statement)

            async def scalars(self, statement):
                return database.scalars(statement)

            async def execute(self, statement):
                return database.execute(statement)

            async def commit(self):
                database.commit()

            async def refresh(self, row):
                database.refresh(row)

            def add(self, row):
                database.add(row)

        session = Adapter()
        for user in (first, second):
            await acne.grant(user, AcneConsentInput(consent_to_store=True), session)
            await acne.save(user, AcneInput(local_date="2026-01-01", response="yes"), session)
        await acne.save(first, AcneInput(local_date="2026-01-01", response="no"), session)
        assert (await acne.history(first, 30, session))["items"][0]["response"] == "no"
        assert (await acne.history(second, 30, session))["items"][0]["response"] == "yes"
        await acne.remove(first, date(2026, 1, 1), session)
        assert (await acne.history(first, 30, session))["items"] == []
        await acne.save(first, AcneInput(local_date="2026-01-02", response="unsure"), session)
        await acne.withdraw(first, session)
        assert not await acne.consent_active(session, first)
        assert await acne.consent_active(session, second)
        assert (
            database.scalar(select(AcneObservation).where(AcneObservation.user_id == first)) is None
        )
        assert len((await acne.history(second, 30, session))["items"]) == 1
        await acne.grant(first, AcneConsentInput(consent_to_store=True), session)
        assert (await acne.history(first, 30, session))["items"] == []
    engine.dispose()


@pytest.mark.asyncio
async def test_training_consent_real_db_prerequisites_idempotence_withdrawal(enabled):
    engine = create_engine("sqlite:///:memory:")
    for table in (
        User.__table__,
        Consent.__table__,
        AcneObservation.__table__,
        DailyHealthEntry.__table__,
    ):
        table.create(engine)
    with SQLSession(engine, expire_on_commit=False) as database:
        user, other = uuid4(), uuid4()
        database.add_all([User(id=user), User(id=other)])
        database.commit()

        class Adapter:
            async def scalar(self, statement):
                return database.scalar(statement)

            async def scalars(self, statement):
                return database.scalars(statement)

            async def execute(self, statement):
                return database.execute(statement)

            async def commit(self):
                database.commit()

            def add(self, row):
                database.add(row)

        session = Adapter()
        payload = AcneTrainingConsentInput(consent_to_train_acne=True)
        with pytest.raises(HTTPException) as error:
            await acne.grant_training(user, payload, session)
        assert error.value.status_code == 410
        await acne.grant(user, AcneConsentInput(consent_to_store=True), session)
        with pytest.raises(HTTPException):
            await acne.grant_training(user, payload, session)
        database.add(Consent(user_id=user, version=MODEL_TRAINING_CONSENT_VERSION))
        database.add(Consent(user_id=other, version=ACNE_MODEL_TRAINING_CONSENT_VERSION))
        database.add(
            AcneObservation(user_id=user, local_date=date(2026, 1, 1), response="no", regions=[])
        )
        database.commit()
        # Legacy consent survives feature removal; no new consent may be granted.
        database.add(Consent(user_id=user, version=ACNE_MODEL_TRAINING_CONSENT_VERSION))
        database.commit()
        with pytest.raises(HTTPException) as error:
            await acne.grant_training(user, payload, session)
        assert error.value.status_code == 410
        active_rows = database.scalars(
            select(Consent).where(
                Consent.user_id == user,
                Consent.version == ACNE_MODEL_TRAINING_CONSENT_VERSION,
                Consent.revoked_at.is_(None),
            )
        ).all()
        assert len(active_rows) == 1
        assert (await acne.history(user, 30, session))["training_consent_active"] is True
        await acne.withdraw_training(user, session)
        assert not await acne.consent_active(session, user, ACNE_MODEL_TRAINING_CONSENT_VERSION)
        assert await acne.consent_active(session, user)
        assert await acne.consent_active(session, user, MODEL_TRAINING_CONSENT_VERSION)
        assert await acne.consent_active(session, other, ACNE_MODEL_TRAINING_CONSENT_VERSION)
        assert len((await acne.history(user, 30, session))["items"]) == 1
        database.add(Consent(user_id=user, version=ACNE_MODEL_TRAINING_CONSENT_VERSION))
        database.commit()
        await acne.withdraw(user, session)
        assert not await acne.consent_active(session, user, ACNE_MODEL_TRAINING_CONSENT_VERSION)
        assert (await acne.history(user, 30, session))["items"] == []
    engine.dispose()


def test_training_consent_rejects_false_or_extra_fields():
    for payload in [
        {"consent_to_train_acne": False},
        {"consent_to_train_acne": True, "user_id": str(uuid4())},
    ]:
        with pytest.raises(ValidationError):
            AcneTrainingConsentInput(**payload)
