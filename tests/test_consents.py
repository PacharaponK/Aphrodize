from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.schemas.consent import ConsentCreate
from backend.api.v1.routes.consents import create_consent
from backend.core.db.models import Consent, User
from backend.services.analysis_service import create_analysis
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
