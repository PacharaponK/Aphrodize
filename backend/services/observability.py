"""Read-only probes, bounded collection and workflow readiness."""

import asyncio
import logging
from datetime import UTC, datetime

import urllib3
from arq.constants import health_check_key_suffix
from minio import Minio
from sqlalchemy import func, select, text

from backend.core import observability as metrics
from backend.core.config import settings
from backend.core.db.models import Analysis, InferenceRun, TrainingRun
from backend.core.db.session import SessionLocal
from backend.libs.redis_client import get_arq_pool


def expected_queues():
    queues = [q.strip() for q in settings.observability_expected_queues.split(",") if q.strip()]
    if any(q not in {"inference", "training"} for q in queues):
        raise ValueError("Expected queues must be inference and/or training")
    return sorted(set(queues))


async def postgres_probe():
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))


async def redis_probe():
    pool = await get_arq_pool()
    try:
        await pool.ping()
    finally:
        await pool.aclose()


async def minio_probe():
    # SDK timeouts bound the thread itself, not merely its awaiter.
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        http_client=urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=0.5, read=1), retries=False
        ),
    )
    exists = await asyncio.to_thread(client.bucket_exists, settings.minio_bucket)
    if not exists:
        raise RuntimeError("Required storage bucket unavailable")


async def checked(probe):
    try:
        await asyncio.wait_for(probe(), timeout=2)
        return True
    except Exception:
        return False


async def readiness():
    values = await asyncio.gather(*(checked(p) for p in (postgres_probe, redis_probe, minio_probe)))
    dependencies = dict(zip(("postgres", "redis", "minio"), values, strict=True))
    for name, up in dependencies.items():
        metrics.dependency_up.labels(name).set(up)
        metrics.dependency_required.labels(name).set(
            name != "minio" or settings.observability_minio_required
        )
    capabilities = {
        "accounts": dependencies["postgres"],
        "image_storage": dependencies["postgres"] and dependencies["minio"],
        "job_submission": dependencies["postgres"] and dependencies["redis"],
    }
    all_ready = (
        dependencies["postgres"]
        and dependencies["redis"]
        and (dependencies["minio"] or not settings.observability_minio_required)
    )
    return {
        "status": "ready"
        if all_ready
        else "degraded"
        if capabilities["accounts"]
        else "unavailable",
        "dependencies": dependencies,
        "capabilities": capabilities,
    }


async def collect_queues():
    queues = expected_queues()
    if not queues:
        return
    pool = await get_arq_pool()
    try:
        for queue in queues:
            alive = bool(await pool.exists(queue + health_check_key_suffix))
            metrics.worker_up.labels(queue).set(alive)
    finally:
        await pool.aclose()
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        for queue in queues:
            models = (Analysis, InferenceRun) if queue == "inference" else (TrainingRun,)
            waiting, first_waiting, first_running = 0, [], []
            for model in models:
                for status, count, first in (
                    await session.execute(
                        select(model.status, func.count(), func.min(model.created_at))
                        .where(model.status.in_(["queued", "running"]))
                        .group_by(model.status)
                    )
                ).all():
                    if first is not None and first.tzinfo is None:
                        first = first.replace(tzinfo=UTC)
                    if status == "queued":
                        waiting += count
                        if first:
                            first_waiting.append(first)
                    elif first:
                        first_running.append(first)
            metrics.queued.labels(queue).set(waiting)
            metrics.oldest.labels(queue).set(
                max(0, (now - min(first_waiting)).total_seconds()) if first_waiting else 0
            )
            metrics.running_age.labels(queue).set(
                max(0, (now - min(first_running)).total_seconds()) if first_running else 0
            )


def collect_uv():
    from backend.services.uv_lifecycle import ARTIFACTS, read_json
    from backend.services.uv_service import load_recommendation

    metrics.uv_up.set(0)
    metrics.uv_quality.set(0)
    # Keep last successful timestamp even when the next read fails.
    try:
        forecasts = [load_recommendation(city) for city in ("bangkok", "songkhla", "chiang_mai")]
        generated = min(datetime.fromisoformat(f["generated_at"]) for f in forecasts)
        age = (datetime.now(UTC) - generated).total_seconds()
        metrics.uv_generated.set(generated.timestamp())
        metrics.uv_up.set(-300 <= age <= 8 * 3600)
        quality = read_json(ARTIFACTS / "monitoring.json")
        quality_age = (
            datetime.now(UTC) - datetime.fromisoformat(quality["generated_at"])
        ).total_seconds()
        metrics.uv_quality.set(
            quality["status"] not in {"alert", "stale", "unavailable"}
            and -300 <= quality_age <= 8 * 3600
        )
    except (OSError, ValueError, KeyError, TypeError):
        pass


async def collect_once():
    metrics.uv_enabled.set(settings.observability_uv_enabled)
    try:
        await readiness()
        await asyncio.wait_for(collect_queues(), timeout=3)
        if settings.observability_uv_enabled:
            await asyncio.to_thread(collect_uv)
        metrics.collector_success.set(1)
    except Exception:
        metrics.collector_success.set(0)
        logging.getLogger(__name__).exception("", extra={"event": "collector_failed"})
    finally:
        metrics.collector_at.set(datetime.now(UTC).timestamp())


async def collect_forever():
    while True:
        await collect_once()
        await asyncio.sleep(30)
