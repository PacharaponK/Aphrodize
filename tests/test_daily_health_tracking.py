from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.api.v1.routes.training import serialize
from backend.services import daily_health_tracking as tracking
from backend.workers import trainer_worker


def test_tracking_logs_aggregate_metrics_not_private_artifacts(monkeypatch):
    events = []

    class Client:
        def __init__(self, **_kwargs):
            pass

        def get_experiment_by_name(self, name):
            assert name == "daily-health-next-day"
            return SimpleNamespace(experiment_id="test")

        def create_run(self, experiment_id, tags):
            events.append(tags)
            return SimpleNamespace(info=SimpleNamespace(run_id="tracked-run"))

        def log_param(self, _run_id, key, value):
            events.append((key, value))

        def log_metric(self, _run_id, key, value):
            events.append((key, value))

        def set_terminated(self, _run_id, status):
            events.append(status)

    monkeypatch.setattr(tracking, "MlflowClient", Client)
    version = SimpleNamespace(
        version_id="candidate-test", model_family="daily-health",
        training_records=100, participant_count=5,
        metrics={"test": {"thirst": {"mae": 0.7, "r2": None}}, "temporal_test": None},
    )
    assert tracking.track_daily_health_candidate(version) == "tracked-run"
    assert ("test.thirst.mae", 0.7) in events
    assert events[-1] == "FINISHED"
    assert events[0]["tracking_scope"] == "aggregate_metrics_only"
    # Client deliberately has no artifact/data APIs: private rows/models cannot be uploaded.


@pytest.mark.asyncio
async def test_worker_links_candidate_to_mlflow_without_deploying(monkeypatch):
    version = SimpleNamespace(status="candidate", mlflow_run_id=None)
    commits = []

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def commit(self):
            commits.append(True)

    async def train(_session):
        return version

    monkeypatch.setattr(trainer_worker, "SessionLocal", Session)
    monkeypatch.setattr(trainer_worker, "train_daily_health_candidate", train)
    monkeypatch.setattr(trainer_worker, "track_daily_health_candidate", lambda _: "run-id")
    await trainer_worker.run_daily_health_candidate_training({})
    assert version.mlflow_run_id == "run-id"
    assert version.status == "candidate"
    assert commits == [True]


@pytest.mark.asyncio
async def test_tracking_outage_preserves_candidate_and_surfaces_failure(monkeypatch):
    version = SimpleNamespace(status="candidate", mlflow_run_id=None)

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

    async def train(_session):
        return version

    def unavailable(_version):
        raise ConnectionError("tracking unavailable")

    monkeypatch.setattr(trainer_worker, "SessionLocal", Session)
    monkeypatch.setattr(trainer_worker, "train_daily_health_candidate", train)
    monkeypatch.setattr(trainer_worker, "track_daily_health_candidate", unavailable)
    with pytest.raises(ConnectionError):
        await trainer_worker.run_daily_health_candidate_training({})
    assert version.status == "candidate"
    assert version.mlflow_run_id is None


@pytest.mark.parametrize("family,expected", [
    ("time_series", "metadata_only"), ("tabular", "metadata_only"),
    ("image_segmentation", "model_training"),
])
def test_training_api_explains_execution_kind(family, expected):
    run = SimpleNamespace(
        id=uuid4(), model_family=family, dataset_uri="test://dataset", status="queued",
        mlflow_run_id=None, created_at=datetime.now(UTC),
    )
    assert serialize(run).execution_kind == expected
