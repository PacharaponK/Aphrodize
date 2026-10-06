"""Model approval uses separate operator credentials and server-derived identity."""

import pytest
from fastapi.security import HTTPBasicCredentials
from fastapi.testclient import TestClient

from backend.api.deps import require_model_reviewer
from backend.core.config import settings
from backend.core.db.session import get_session
from backend.main import app


@pytest.fixture
def review_credentials(monkeypatch):
    monkeypatch.setattr(settings, "api_username", "service-test")
    monkeypatch.setattr(settings, "api_password", "service-test-password")
    monkeypatch.setattr(settings, "admin_username", "operator-test")
    monkeypatch.setattr(settings, "admin_password", "operator-test-password")


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "/model-versions", None),
    ("GET", "/model-deployment", None),
    ("GET", "/model-deployment/events", None),
    ("PUT", "/model-deployment", {
        "version_id": "candidate-test", "approval_reason": "Reviewed all holdout metrics",
    }),
    ("POST", "/model-deployment/rollback", {"reason": "Observed a model regression"}),
])
def test_service_credentials_cannot_access_review_routes(review_credentials, method, path, payload):
    response = TestClient(app).request(
        method, f"/api/v1/daily-health{path}", json=payload,
        auth=("service-test", "service-test-password"),
    )
    assert response.status_code == 401


def test_admin_can_access_review_route_without_service_credentials(review_credentials):
    class Session:
        async def get(self, *_args):
            return None

    async def fake_session():
        yield Session()

    app.dependency_overrides[get_session] = fake_session
    try:
        response = TestClient(app).get(
            "/api/v1/daily-health/model-deployment",
            auth=("operator-test", "operator-test-password"),
        )
        assert response.status_code == 200
        assert response.json()["active_version_id"] is None
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_reviewer_identity_is_from_authenticated_credentials(review_credentials):
    assert require_model_reviewer(HTTPBasicCredentials(
        username="operator-test", password="operator-test-password",
    )) == "operator-test"


def test_request_body_cannot_spoof_reviewer_identity(review_credentials):
    response = TestClient(app).put(
        "/api/v1/daily-health/model-deployment",
        auth=("operator-test", "operator-test-password"),
        json={
            "version_id": "test",
            "approval_reason": "Reviewed all holdout metrics",
            "actor": "fake",
        },
    )
    assert response.status_code == 422


def test_shared_service_and_admin_credentials_fail_closed(review_credentials, monkeypatch):
    monkeypatch.setattr(settings, "admin_username", settings.api_username)
    monkeypatch.setattr(settings, "admin_password", settings.api_password)
    response = TestClient(app).get(
        "/api/v1/daily-health/model-deployment",
        auth=("service-test", "service-test-password"),
    )
    assert response.status_code == 503


def test_unconfigured_admin_fails_closed(review_credentials, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "")
    response = TestClient(app).get(
        "/api/v1/daily-health/model-deployment", auth=("operator-test", "invalid"),
    )
    assert response.status_code == 503
