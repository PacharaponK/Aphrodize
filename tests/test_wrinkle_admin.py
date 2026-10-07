"""Runnable lifecycle checks: pinned data, candidate gates, queue failure and safe deployment."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.api.v1.routes import wrinkle_admin
from backend.core.config import settings
from backend.core.db.models import TrainingRun
from backend.services import wrinkle_datasets as datasets
from backend.services import wrinkle_lifecycle as lifecycle
from backend.workers import trainer_worker


def evaluation(value=0.8):
    metrics = {
        f"{s}_{m}": value for s in ("validation", "test") for m in ("dice", "iou", "mean_dice")
    }
    metrics.update(validation_positive_samples=1, test_positive_samples=1)
    return {"candidate": metrics, "baseline": dict(metrics), "base_checkpoint_sha256": "b" * 64}


def test_gate_rejects_missing_nan_and_regression():
    assert lifecycle.quality_gate(evaluation())["passed"]
    assert not lifecycle.quality_gate({})["passed"]
    for value in (float("nan"), 0.59, 0.79):
        result = evaluation()
        result["candidate"]["test_dice"] = value
        assert not lifecycle.quality_gate(result)["passed"]


def test_admin_auth_and_request_validation(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "reviewer")
    monkeypatch.setattr(settings, "admin_password", "test-review-password")
    app = FastAPI()
    app.include_router(wrinkle_admin.router, prefix="/admin/wrinkle")
    client = TestClient(app)
    assert client.get("/admin/wrinkle").status_code == 401
    assert (
        client.post(
            "/admin/wrinkle", auth=("wrong", "wrong"), json={"action": "retrain"}
        ).status_code
        == 401
    )
    for body in (
        {"action": "retrain", "epochs": 21},
        {"action": "promote", "version": "../escape"},
        {"action": "retrain", "epochs": True},
    ):
        assert (
            client.post(
                "/admin/wrinkle", auth=("reviewer", "test-review-password"), json=body
            ).status_code
            == 422
        )


class MemorySession:
    def __init__(self, run=None):
        self.run = run
        self.state = SimpleNamespace(state={"active": "initial", "history": [], "pending": None})

    async def get(self, model, key):
        return self.run if self.run and self.run.id == key else None

    async def scalar(self, _):
        return None

    def add(self, run):
        run.id = uuid4()
        run.created_at = datetime.now(UTC)
        self.run = run

    async def commit(self):
        pass

    async def refresh(self, _):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


async def fake_deployment(session, **_):
    return session.state


async def fake_dataset(*_):
    return None, {"rights_reference": "test-license"}


@pytest.mark.asyncio
async def test_queue_failure_marks_run_failed_and_stale_base_cannot_submit(monkeypatch):
    monkeypatch.setattr(lifecycle, "deployment", fake_deployment)
    monkeypatch.setattr(lifecycle, "checked_dataset", fake_dataset)
    session = MemorySession()

    async def unavailable():
        raise RuntimeError("queue offline")

    monkeypatch.setattr(lifecycle, "get_arq_pool", unavailable)
    with pytest.raises(HTTPException) as error:
        await lifecycle.submit(session, "approved://test@hash", 1, "old-version", "reviewer")
    assert error.value.status_code == 409 and session.run is None
    with pytest.raises(HTTPException) as error:
        await lifecycle.submit(session, "approved://test@hash", 1, "initial", "reviewer")
    assert error.value.status_code == 503 and session.run.status == "failed"


@pytest.mark.asyncio
async def test_promote_then_rollback_and_failed_smoke_preserve_active(monkeypatch, tmp_path):
    run = TrainingRun(
        id=uuid4(),
        model_family="image_segmentation",
        dataset_uri="test",
        status="awaiting_approval",
        config={
            "base_version": "initial",
            "package": True,
            "evaluation": evaluation(),
            "checkpoint_sha256": "a" * 64,
        },
    )
    session = MemorySession(run)
    monkeypatch.setattr(lifecycle, "deployment", fake_deployment)
    monkeypatch.setattr(lifecycle, "checked_dataset", fake_dataset)
    monkeypatch.setattr(lifecycle, "package_path", lambda _: tmp_path)
    monkeypatch.setattr(trainer_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(trainer_worker, "smoke_checkpoint", lambda *_: None)
    monkeypatch.setattr(trainer_worker, "checkpoint_hash", lambda *_: "b" * 64)
    pending = {
        "version": str(run.id),
        "expected_active": "initial",
        "actor": "reviewer",
        "action": "promote",
        "at": lifecycle.now(),
    }
    session.state.state["pending"] = pending
    await trainer_worker.activate_wrinkle({}, pending)
    assert session.state.state["active"] == str(run.id)
    assert session.state.state["history"][-1]["actor"] == "reviewer"
    rollback = {
        **pending,
        "version": "initial",
        "expected_active": str(run.id),
        "action": "rollback",
    }
    session.state.state["pending"] = rollback

    def broken(*_):
        raise ValueError("broken checkpoint")

    monkeypatch.setattr(trainer_worker, "smoke_checkpoint", broken)
    await trainer_worker.activate_wrinkle({}, rollback)
    assert session.state.state["active"] == str(run.id)
    assert session.state.state["pending"] is None
    monkeypatch.setattr(trainer_worker, "smoke_checkpoint", lambda *_: None)
    session.state.state["pending"] = rollback
    await trainer_worker.activate_wrinkle({}, rollback)
    assert session.state.state["active"] == "initial"


@pytest.mark.asyncio
async def test_revoked_or_regranted_consent_cannot_reuse_snapshot(monkeypatch):
    from backend.services import annotation_service

    async def allowed(*_):
        return True

    monkeypatch.setattr(annotation_service, "has_annotation_consent", allowed)
    user = uuid4()
    data = {
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "consent_records": [{"user_id": str(user), "consent_id": str(uuid4())}],
    }

    async def regranted(*_):
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(datasets, "training_consent", regranted)
    with pytest.raises(ValueError, match="withdrawn or changed"):
        await datasets.check_user_dataset(None, data)
    data["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="expired"):
        await datasets.check_user_dataset(None, data)


def test_reviewed_brush_export_matches_pixels_and_rejects_wrong_annotation():
    from label_studio_sdk.converter.brush import mask2rle

    mask = np.zeros((1024, 1024), dtype=np.uint8)
    mask[40:45, 60:80] = 255
    task = {
        "annotations": [
            {
                "id": 11,
                "was_cancelled": False,
                "result": [
                    {
                        "type": "brushlabels",
                        "original_width": 1024,
                        "original_height": 1024,
                        "value": {"brushlabels": ["Wrinkle"], "rle": mask2rle(mask)},
                    }
                ],
            }
        ]
    }
    np.testing.assert_array_equal(datasets.reviewed_mask(task, 11), mask)
    with pytest.raises(ValueError, match="missing or cancelled"):
        datasets.reviewed_mask(task, 12)
    task["annotations"][0]["result"][0]["value"]["rle"][:4] = [255] * 4
    with pytest.raises(ValueError, match="Invalid or oversized"):
        datasets.reviewed_mask(task, 11)
