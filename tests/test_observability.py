import asyncio
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from backend.api.deps import require_api_credentials
from backend.api.v1.routes.monitoring import router
from backend.core import observability as obs
from backend.services import observability as probes
from scripts.configure_observability import configure
from scripts.external_probe import advance, validate_urls


def test_logs_drop_private_messages_exception_text_and_extra():
    try:
        raise ValueError("password=secret user@example.com")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "sqlalchemy", logging.ERROR, __file__, 1, "photo=%s", ("private-image",), sys.exc_info()
        )
    record.token = "private-token"
    output = obs.SafeJsonFormatter().format(record)
    assert all(s not in output for s in ("secret", "example.com", "private-image", "private-token"))
    assert json.loads(output)["error_type"] == "ValueError"


def test_http_correlation_and_route_cardinality():
    app = FastAPI()
    app.add_middleware(obs.ObserveHTTP)

    @app.get("/items/{identifier}")
    async def item(identifier: str):
        return {"correlation": obs.request_id.get()}

    with TestClient(app) as client:
        response = client.get(
            "/items/private-user?token=secret", headers={"x-request-id": "a" * 32}
        )
        assert response.json()["correlation"] == response.headers["x-request-id"] == "a" * 32
        assert client.get("/random-private-path").status_code == 404
        fresh = client.get("/items/test", headers={"x-request-id": "private@example.com"})
        assert len(fresh.headers["x-request-id"]) == 32
    assert obs.request_id.get() == ""
    metrics = generate_latest(obs.registry).decode()
    assert 'route="/items/{identifier}"' in metrics
    assert 'route="unmatched"' in metrics
    assert "private-user" not in metrics and "random-private-path" not in metrics


@pytest.mark.asyncio
async def test_enqueue_correlates_without_changing_private_arguments():
    class Pool:
        async def enqueue_job(self, function, *args, **kwargs):
            self.call = function, args, kwargs
            return SimpleNamespace(job_id="job-1")

    pool = Pool()
    token = obs.request_id.set("b" * 32)
    try:
        await obs.enqueue_job(pool, "function", "private-id", _queue_name="inference")
    finally:
        obs.request_id.reset(token)
    assert pool.call == (
        "function",
        ("private-id",),
        {"_queue_name": "inference", "_request_id": "b" * 32},
    )


@pytest.mark.asyncio
async def test_job_records_business_failure_rejection_and_restores_context():
    @obs.observed_job
    async def check_job(ctx, outcome):
        assert obs.request_id.get() == "c" * 32
        ctx["telemetry_outcome"] = outcome

    ctx = {"job_id": "opaque", "score": time.time() * 1000 - 1000}
    for outcome in ("failed", "rejected"):
        before = obs.jobs.labels("check_job", outcome)._value.get()
        await check_job(ctx, outcome, _request_id="c" * 32)
        assert obs.jobs.labels("check_job", outcome)._value.get() == before + 1
    assert obs.request_id.get() == obs.job_id.get() == ""

    @obs.observed_job
    async def failing(ctx):
        raise RuntimeError("private data")

    with pytest.raises(RuntimeError):
        await failing({})
    assert obs.jobs.labels("failing", "failed")._value.get() == 1


@pytest.mark.asyncio
async def test_readiness_preserves_accounts_during_storage_failure(monkeypatch):
    async def ready():
        pass

    async def unavailable():
        raise RuntimeError("secret")

    monkeypatch.setattr(probes, "postgres_probe", ready)
    monkeypatch.setattr(probes, "redis_probe", unavailable)
    monkeypatch.setattr(probes, "minio_probe", unavailable)
    response = await probes.readiness()
    assert response["status"] == "degraded"
    assert response["capabilities"] == {
        "accounts": True,
        "image_storage": False,
        "job_submission": False,
    }


def test_metrics_and_readiness_require_existing_service_auth():
    app = FastAPI()
    app.include_router(router, dependencies=[Depends(require_api_credentials)])
    with TestClient(app) as client:
        assert client.get("/metrics").status_code == 401
        assert client.get("/ready").status_code == 401


@pytest.mark.asyncio
async def test_collection_failure_does_not_escape(monkeypatch):
    async def failed():
        raise ConnectionError("secret")

    monkeypatch.setattr(probes, "readiness", failed)
    await probes.collect_once()
    assert obs.collector_success._value.get() == 0
    assert obs.collector_at._value.get() > time.time() - 10


@pytest.mark.asyncio
async def test_probe_timeout_is_bounded():
    async def stuck():
        await asyncio.sleep(60)

    started = time.monotonic()
    assert not await probes.checked(stuck)
    assert time.monotonic() - started < 3


def test_private_config_preserves_password_and_optional_deployments(tmp_path):
    configure(
        {
            "API_PASSWORD": "secret$with:syntax",
            "API_USERNAME": "operator",
            "OBS_EXPECTED_QUEUES": "inference",
            "OBS_INFERENCE_TARGET": "tunnel:19101",
        },
        tmp_path,
    )
    assert (tmp_path / "api-password").read_text() == "secret$with:syntax"
    assert json.loads((tmp_path / "targets/workers.json").read_text())[0]["targets"] == [
        "tunnel:19101"
    ]
    assert json.loads((tmp_path / "targets/gpu.json").read_text()) == []
    assert "secret$with" not in (tmp_path / "prometheus.yml").read_text()


def test_external_outage_recovery_and_failed_delivery_retry():
    state = {}
    for i in range(3):
        assert advance(state, False, i * 30) is None
    assert advance(state, False, 90) == "down"
    assert advance(state, False, 120) == "down"
    state.update(notified="down")
    state.pop("pending")
    assert advance(state, False, 150) is None
    assert advance(state, True, 180) == "recovered"
    assert advance(state, False, 210) is None
    assert advance(state, True, 240) == "recovered"
    validate_urls("https://example.com/api/health", "https://discord.com/api/webhooks/1/token")
    with pytest.raises(ValueError):
        validate_urls("http://example.com", "https://evil.example/api/webhooks/1/token")


@pytest.mark.asyncio
async def test_queue_aggregate_tracks_orphans_and_heartbeat_without_payloads(monkeypatch):
    now = datetime.now(UTC)

    class Pool:
        async def exists(self, key):
            assert key.startswith("inference")
            return 0

        async def aclose(self):
            pass

    class Session:
        async def __aenter__(self):
            self.count = 0
            return self

        async def __aexit__(self, *_args):
            pass

        async def execute(self, query):
            self.count += 1
            assert "input_data" not in str(query) and "object_key" not in str(query)
            rows = (
                [
                    ("queued", 2, now - timedelta(seconds=600)),
                    ("running", 1, now - timedelta(seconds=1000)),
                ]
                if self.count == 1
                else [("queued", 1, now - timedelta(seconds=300))]
            )
            return SimpleNamespace(all=lambda: rows)

    async def pool():
        return Pool()

    monkeypatch.setattr(probes.settings, "observability_expected_queues", "inference")
    monkeypatch.setattr(probes, "get_arq_pool", pool)
    monkeypatch.setattr(probes, "SessionLocal", Session)
    await probes.collect_queues()
    assert obs.worker_up.labels("inference")._value.get() == 0
    assert obs.queued.labels("inference")._value.get() == 3
    assert obs.oldest.labels("inference")._value.get() >= 600
    assert obs.running_age.labels("inference")._value.get() >= 1000


def test_uv_unavailable_clears_ready_gauges(monkeypatch):
    from backend.services import uv_service

    def failed(_city):
        raise ValueError("unavailable")

    monkeypatch.setattr(uv_service, "load_recommendation", failed)
    obs.uv_up.set(1)
    obs.uv_quality.set(1)
    probes.collect_uv()
    assert obs.uv_up._value.get() == obs.uv_quality._value.get() == 0
