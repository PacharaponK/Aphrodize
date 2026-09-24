from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.v1.routes import analyses


class FakeSession:
    def __init__(self, item):
        self.item = item

    async def get(self, _model, _identifier):
        return self.item


@pytest.mark.asyncio
async def test_artifact_is_private_and_expires(monkeypatch) -> None:
    item = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        result={"artifacts_expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()},
    )
    monkeypatch.setattr(analyses, "get_bytes", lambda _key: b"private-png")

    response = await analyses.get_analysis_artifact(item.id, "mask", FakeSession(item))
    assert response.body == b"private-png"
    assert response.headers["cache-control"] == "private, no-store"

    item.result["artifacts_expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(HTTPException) as error:
        await analyses.get_analysis_artifact(item.id, "mask", FakeSession(item))
    assert error.value.status_code == 410
