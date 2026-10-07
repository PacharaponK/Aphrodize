from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.schemas.consent import ConsentCreate
from backend.api.v1.routes.consents import (
    create_consent,
    grant_analysis_consent,
    read_image_consents,
    revoke_analysis_consent,
)
from backend.core.db.models import Consent, User
from backend.services.analysis_service import create_analysis
from backend.services.annotation_service import ANNOTATION_CONSENT_VERSION
from backend.services.tokens import read_access_token


@pytest.mark.asyncio
async def test_consent_saves_user_before_foreign_key() -> None:
    class Session:
        def __init__(self):
            self.added = []
            self.flushed = False

        def add(self, item):
            if isinstance(item, Consent):
                assert self.flushed
            self.added.append(item)

        async def flush(self):
            assert len(self.added) == 1 and isinstance(self.added[0], User)
            self.flushed = True

        async def commit(self):
            assert self.flushed and len(self.added) == 2

        async def refresh(self, item):
            item.id = uuid4()
            item.accepted_at = datetime.now(UTC)

    session = Session()
    response = await create_consent(ConsentCreate(version="1.0"), session)
    assert response.user_id == session.added[0].id
    assert response.consent_id == session.added[1].id
    assert response.access_token is not None
    assert read_access_token(response.access_token) == response.user_id


@pytest.mark.asyncio
async def test_image_upload_requires_image_analysis_consent() -> None:
    class Session:
        async def scalar(self, statement):
            assert "1.0" in statement.compile().params.values()
            return None

    with pytest.raises(HTTPException) as error:
        await create_analysis(Session(), uuid4(), None)
    assert error.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [False, True])
async def test_grant_analysis_consent_for_existing_user(active: bool) -> None:
    owner = uuid4()

    class Session:
        def __init__(self):
            self.added = []
            self.committed = False

        async def get(self, model, user_id):
            assert model is User and user_id == owner
            return User(id=owner)

        async def scalar(self, statement):
            query = statement.compile()
            assert owner in query.params.values()
            assert "1.0" in query.params.values()
            assert "revoked_at IS NULL" in str(query)
            return uuid4() if active else None

        def add(self, consent):
            self.added.append(consent)

        async def commit(self):
            self.committed = True

    session = Session()
    assert await grant_analysis_consent(owner, session) == {"status": "granted"}
    assert session.committed is (not active)
    assert len(session.added) == (0 if active else 1)
    if not active:
        assert session.added[0].user_id == owner
        assert session.added[0].version == "1.0"


@pytest.mark.asyncio
async def test_grant_analysis_consent_rejects_unknown_user() -> None:
    class Session:
        async def get(self, _model, _id):
            return None

    with pytest.raises(HTTPException) as error:
        await grant_analysis_consent(uuid4(), Session())
    assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("analysis,annotations", [(False, False), (True, False), (True, True)])
async def test_read_saved_image_consents(analysis: bool, annotations: bool) -> None:
    owner = uuid4()

    class Session:
        async def get(self, _model, user_id):
            assert user_id == owner
            return User(id=owner)

        async def scalars(self, statement):
            query = statement.compile()
            assert owner in query.params.values()
            assert "revoked_at IS NULL" in str(query)
            return self

        def all(self):
            return (["1.0"] if analysis else []) + (
                [ANNOTATION_CONSENT_VERSION] if annotations else []
            )

    assert await read_image_consents(owner, Session()) == {
        "analysis": analysis, "annotations": annotations, "training": False,
    }


@pytest.mark.asyncio
async def test_withdraw_analysis_consent_preserves_other_scopes() -> None:
    owner = uuid4()

    class Session:
        committed = False

        async def get(self, _model, user_id):
            assert user_id == owner
            return User(id=owner)

        async def execute(self, statement):
            query = statement.compile()
            assert query.params["user_id_1"] == owner
            assert query.params["version_1"] == "1.0"
            assert isinstance(query.params["revoked_at"], datetime)

        async def commit(self):
            self.committed = True

    session = Session()
    await revoke_analysis_consent(owner, session)
    assert session.committed


@pytest.mark.asyncio
@pytest.mark.parametrize("route", [read_image_consents, revoke_analysis_consent])
async def test_saved_consent_routes_reject_unknown_user(route) -> None:
    class Session:
        async def get(self, _model, _id):
            return None

    with pytest.raises(HTTPException) as error:
        await route(uuid4(), Session())
    assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,project,available",
    [("", 0, False), ("token", 0, False), ("", 7, False), ("token", 7, True)],
)
async def test_annotation_capability_requires_token_and_project(
    monkeypatch, key, project, available
):
    from backend.api.v1.routes.health import capabilities
    from backend.core.config import settings

    monkeypatch.setattr(settings, "label_studio_api_key", key)
    monkeypatch.setattr(settings, "label_studio_project_id", project)
    assert await capabilities() == {"annotation_review_available": available}
