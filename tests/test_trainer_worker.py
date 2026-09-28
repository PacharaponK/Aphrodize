from datetime import UTC

import pytest

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
