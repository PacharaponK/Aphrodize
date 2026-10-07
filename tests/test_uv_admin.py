"""Admin UV review rejects service credentials, forged actors and unsafe deployments."""

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from backend.services import uv_lifecycle as lifecycle
from scripts import uv_mlops


@pytest.fixture
def review_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "api_username", "service")
    monkeypatch.setattr(settings, "api_password", "service-password")
    monkeypatch.setattr(settings, "admin_username", "operator")
    monkeypatch.setattr(settings, "admin_password", "operator-password")
    monkeypatch.setattr(lifecycle, "MODELS", tmp_path / "models")
    monkeypatch.setattr(lifecycle, "ARTIFACTS", tmp_path / "artifacts")
    lifecycle.atomic_json(
        lifecycle.MODELS / "active.json",
        {
            "active": "uv-current",
            "history": [{"from": "uv-previous", "to": "uv-current"}],
        },
    )
    for version in ("uv-current", "uv-candidate"):
        bundle = lifecycle.bundle_path(version)
        (bundle / "models").mkdir(parents=True)
        for city in lifecycle.CITIES:
            (bundle / "models" / f"{city}.pkl").write_bytes(b"test model")
        (bundle / "dataset.csv").write_text("frozen data", encoding="utf-8")
        lifecycle.atomic_json(bundle / "artifacts/metrics.json", {})
        lifecycle.seal_bundle(
            bundle,
            {
                "source_sha256": lifecycle.digest(bundle / "dataset.csv"),
                "trained_through": dict.fromkeys(lifecycle.CITIES, "2026-09-28"),
            },
        )
    bundle = lifecycle.bundle_path("uv-candidate")
    lifecycle.atomic_json(bundle / "artifacts/evaluation.json", {"cities": {}})
    score = lifecycle.score_pair([8.0] * 14, [8.0] * 14)
    comparison = dict.fromkeys(("candidate", "incumbent", "persistence"), score)
    lifecycle.atomic_json(
        bundle / "gate.json",
        {
            "passed": True,
            "base_version": "uv-current",
            "cities": {
                c: {h: {**comparison, "passed": True} for h in ("h1", "h2")}
                for c in lifecycle.CITIES
            },
            "source_sha256": lifecycle.digest(bundle / "dataset.csv"),
            "manifest_sha256": lifecycle.digest(bundle / "manifest.json"),
            "evaluation_sha256": lifecycle.digest(bundle / "artifacts/evaluation.json"),
        },
    )
    lifecycle.atomic_json(bundle / "tracking.json", {"run_id": "test-run"})
    lifecycle.atomic_json(
        lifecycle.ARTIFACTS / "pipeline_status.json",
        {
            "status": "awaiting_review",
            "version": "uv-candidate",
        },
    )
    return TestClient(app)


AUTH = ("operator", "operator-password")
PAYLOAD = {"action": "promote", "version": "uv-candidate", "expected_active": "uv-current"}


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_service_cannot_review_uv(review_registry, method):
    response = review_registry.request(
        method, "/api/v1/admin/uv", json=PAYLOAD, auth=("service", "service-password")
    )
    assert response.status_code == 401


def test_admin_overview_and_invalid_candidate(review_registry):
    response = review_registry.get("/api/v1/admin/uv", auth=AUTH)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["candidate"]["can_promote"] is True
    (lifecycle.bundle_path("uv-candidate") / "models/bangkok.pkl").write_bytes(b"tampered")
    assert (
        review_registry.get("/api/v1/admin/uv", auth=AUTH).json()["candidate"]["can_promote"]
        is False
    )
    assert review_registry.post("/api/v1/admin/uv", auth=AUTH, json=PAYLOAD).status_code == 409


def test_promote_uses_authenticated_actor(review_registry, monkeypatch):
    calls = []
    monkeypatch.setattr(uv_mlops, "publish", lambda *args: calls.append(args))
    response = review_registry.post("/api/v1/admin/uv", auth=AUTH, json=PAYLOAD)
    assert response.status_code == 200
    assert calls == [("uv-candidate", "operator", "promote", "uv-current")]


@pytest.mark.parametrize("changes", [{"actor": "forged"}, {"version": "../escape"}])
def test_invalid_action_payload_is_rejected(review_registry, changes):
    assert (
        review_registry.post("/api/v1/admin/uv", auth=AUTH, json={**PAYLOAD, **changes}).status_code
        == 422
    )


def test_stale_approval_and_rollback_are_rejected(review_registry, monkeypatch):
    def no_publish(*_args):
        pytest.fail("stale action must not publish")

    monkeypatch.setattr(uv_mlops, "publish", no_publish)
    for action, target in (("promote", "uv-candidate"), ("rollback", "uv-previous")):
        response = review_registry.post(
            "/api/v1/admin/uv",
            auth=AUTH,
            json={
                "action": action,
                "version": target,
                "expected_active": "uv-stale",
            },
        )
        assert response.status_code == 409


def test_rollback_checks_target_and_records_operator(review_registry, monkeypatch):
    calls = []
    monkeypatch.setattr(uv_mlops, "publish", lambda *args: calls.append(args))
    payload = {"action": "rollback", "version": "uv-previous", "expected_active": "uv-current"}
    assert (
        review_registry.post(
            "/api/v1/admin/uv",
            auth=AUTH,
            json={
                **payload,
                "version": "uv-other",
            },
        ).status_code
        == 409
    )
    assert review_registry.post("/api/v1/admin/uv", auth=AUTH, json=payload).status_code == 200
    assert calls == [("uv-previous", "operator", "rollback", "uv-current")]


def test_busy_registry_returns_retryable_conflict(review_registry):
    with lifecycle.deployment_lock():
        assert review_registry.post("/api/v1/admin/uv", auth=AUTH, json=PAYLOAD).status_code == 409
