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
@pytest.mark.parametrize("kind", ["mask", "overlay", "regions", "outline"])
async def test_artifact_is_private_and_expires(monkeypatch, kind) -> None:
    item = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        result={"artifacts_expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()},
    )
    monkeypatch.setattr(analyses, "get_bytes", lambda _key: b"private-png")

    response = await analyses.get_analysis_artifact(
        item.id, kind, item.user_id, FakeSession(item)
    )
    assert response.body == b"private-png"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.media_type == ("image/svg+xml" if kind == "outline" else "image/png")
    with pytest.raises(HTTPException) as unauthorized:
        await analyses.get_analysis_artifact(item.id, kind, uuid4(), FakeSession(item))
    assert unauthorized.value.status_code == 404

    item.result["artifacts_expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(HTTPException) as error:
        await analyses.get_analysis_artifact(item.id, kind, item.user_id, FakeSession(item))
    assert error.value.status_code == 410
