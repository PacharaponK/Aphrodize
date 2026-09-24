from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.api.schemas.consent import ConsentCreate
from backend.api.v1.routes.consents import create_consent
from backend.core.db.models import Consent, User


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
