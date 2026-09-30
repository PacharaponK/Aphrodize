from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient

import backend.main as main


def _patch_database_lifecycle(monkeypatch) -> None:
    async def create_schema() -> None:
        return None

    async def close_database() -> None:
        return None

    monkeypatch.setattr(main, "create_database_schema", create_schema)
    monkeypatch.setattr(main, "close_database", close_database)


def test_api_starts_when_minio_is_not_listening(monkeypatch) -> None:
    _patch_database_lifecycle(monkeypatch)

    def no_storage(*_args, **_kwargs):
        raise ConnectionRefusedError("MinIO is not listening")

    monkeypatch.setattr(main.socket, "create_connection", no_storage)
    monkeypatch.setattr(main, "ensure_bucket", lambda: pytest.fail("should skip MinIO"))

    with TestClient(main.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_starts_when_bucket_setup_fails(monkeypatch) -> None:
    _patch_database_lifecycle(monkeypatch)
    monkeypatch.setattr(
        main.socket,
        "create_connection",
        lambda *_args, **_kwargs: nullcontext(),
    )

    def unavailable_storage() -> None:
        raise ConnectionError("object storage is unavailable")

    monkeypatch.setattr(main, "ensure_bucket", unavailable_storage)

    with TestClient(main.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
