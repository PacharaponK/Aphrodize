from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.routes import users as users_routes
from backend.core.db.session import get_session
from backend.main import app
from backend.services.tokens import create_access_token


def test_private_user_routes_reject_basic_and_other_users() -> None:
    owner, other = uuid4(), uuid4()
    client = TestClient(app)
    bearer = {"Authorization": f"Bearer {create_access_token(other)}"}

    paths = [
        ("GET", f"/api/v1/daily-health/users/{owner}/entries"),
        ("GET", f"/api/v1/daily-health/users/{owner}/profile"),
        ("DELETE", f"/api/v1/daily-health/users/{owner}/profile"),
        ("DELETE", f"/api/v1/daily-health/users/{owner}/data"),
        ("DELETE", f"/api/v1/daily-health/users/{owner}/training-consent"),
        ("DELETE", f"/api/v1/consents/users/{owner}/annotations"),
        ("DELETE", f"/api/v1/users/{owner}/images"),
    ]
    for method, path in paths:
        assert client.request(method, path, headers=bearer).status_code == 403
        assert client.request(method, path, auth=("test-user", "test-password")).status_code == 401


def test_analysis_lookup_requires_record_owner() -> None:
    owner, other, analysis_id = uuid4(), uuid4(), uuid4()

    class Session:
        async def get(self, _model, _id):
            return SimpleNamespace(user_id=owner)

    async def session_override():
        yield Session()

    app.dependency_overrides[get_session] = session_override
    try:
        client = TestClient(app)
        bearer = {"Authorization": f"Bearer {create_access_token(other)}"}
        for suffix in ("", "/artifacts/mask", "/recommendations"):
            response = client.get(f"/api/v1/analyses/{analysis_id}{suffix}", headers=bearer)
            assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_legacy_lifestyle_routes_are_removed() -> None:
    user_id = uuid4()
    client = TestClient(app)
    assert client.get(f"/api/v1/lifestyle-forecast/users/{user_id}").status_code == 404
    assert (
        client.post(f"/api/v1/lifestyle-forecast/users/{user_id}/observations").status_code
        == 404
    )


@pytest.mark.asyncio
async def test_image_deletion_removes_annotations_before_analyses(monkeypatch) -> None:
    owner = uuid4()
    events = []

    class Session:
        async def get(self, _model, _id):
            return object()

        async def execute(self, _statement):
            pass

        async def commit(self):
            pass

        async def scalars(self, _statement):
            return SimpleNamespace(all=lambda: [SimpleNamespace(
                id=uuid4(), object_key="image", user_id=owner
            )])

        async def delete(self, _analysis):
            events.append("analysis")

    async def delete_annotations(_session, _user_id):
        events.append("annotations")

    monkeypatch.setattr(users_routes, "delete_user_annotations", delete_annotations)
    monkeypatch.setattr(users_routes, "remove_objects", lambda _keys: None)
    await users_routes.delete_user_images(owner, Session())
    assert events == ["annotations", "analysis"]
