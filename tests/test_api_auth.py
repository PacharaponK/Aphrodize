from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from fastapi.testclient import TestClient

from backend.api.deps import require_api_credentials
from backend.core.config import settings
from backend.main import app


def test_health_is_public() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200


def test_private_routes_require_basic_authentication() -> None:
    response = TestClient(app).get(f"/api/v1/inference/runs/{uuid4()}")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


def test_configured_basic_credentials_are_accepted() -> None:
    credentials = HTTPBasicCredentials(
        username=settings.api_username, password=settings.api_password
    )
    assert require_api_credentials(credentials) is None


def test_invalid_basic_credentials_are_rejected() -> None:
    credentials = HTTPBasicCredentials(username="invalid", password="invalid")
    try:
        require_api_credentials(credentials)
    except HTTPException as error:
        assert error.status_code == 401
    else:
        raise AssertionError("Invalid credentials must be rejected")
