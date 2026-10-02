from datetime import UTC
from types import SimpleNamespace

import pytest

from backend.core.db.models import TrainingRun
from backend.workers import trainer_worker
from backend.workers.trainer_worker import (
    WorkerSettings,
    check_daily_health_candidate_training,
)


def test_daily_health_candidate_readiness_check_is_scheduled_weekly() -> None:
    jobs = [
        job
        for job in WorkerSettings.cron_jobs
        if job.coroutine is check_daily_health_candidate_training
    ]

    assert len(jobs) == 1
    assert jobs[0].weekday == "mon"
    assert jobs[0].hour == 2
    assert jobs[0].minute == 0
    assert WorkerSettings.timezone is UTC


def test_image_training_uses_curated_dataset_inside_mlflow_run(monkeypatch) -> None:
    events = []

    class MlflowRun:
        info = SimpleNamespace(run_id="candidate-run")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(trainer_worker.mlflow, "set_tracking_uri", events.append)
    monkeypatch.setattr(trainer_worker.mlflow, "start_run", lambda **_: MlflowRun())
    monkeypatch.setattr(trainer_worker.mlflow, "log_params", events.append)
    monkeypatch.setattr(trainer_worker.mlflow, "set_tag", lambda *args: events.append(args))
    monkeypatch.setattr(
        trainer_worker,
        "train_candidate",
        lambda dataset_uri, epochs: events.append((dataset_uri, epochs)),
    )
    run = TrainingRun(
        model_family="image_segmentation",
        dataset_uri="approved://skin@abc123",
        config={"epochs": 3},
    )

    run_id = trainer_worker._train_with_mlflow(run)

    assert run_id == "candidate-run"
    assert events == [
        trainer_worker.settings.mlflow_tracking_uri,
        {"model_family": "image_segmentation", "epochs": 3},
        ("dataset_uri", "approved://skin@abc123"),
        ("approved://skin@abc123", 3),
    ]


@pytest.mark.asyncio
async def test_weekly_check_calls_existing_candidate_readiness_gate(monkeypatch) -> None:
    calls = []

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    async def fake_enqueue_if_ready(session):
        calls.append(session)

    monkeypatch.setattr("backend.workers.trainer_worker.SessionLocal", FakeSession)
    monkeypatch.setattr(
        "backend.workers.trainer_worker.enqueue_candidate_training_if_ready",
        fake_enqueue_if_ready,
    )

    await check_daily_health_candidate_training({})

    assert len(calls) == 1
    assert isinstance(calls[0], FakeSession)
