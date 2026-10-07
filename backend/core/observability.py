"""Bounded metrics and allowlisted logs; telemetry never contains private payloads."""

import asyncio
import contextvars
import functools
import json
import logging
import os
import re
import time
import traceback
from datetime import UTC, datetime
from uuid import uuid4

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server

request_id = contextvars.ContextVar("request_id", default="")
job_id = contextvars.ContextVar("job_id", default="")
registry = CollectorRegistry()
http_requests = Counter(
    "aphrodize_http_requests_total",
    "Completed API requests",
    ["method", "route", "status"],
    registry=registry,
)
http_duration = Histogram(
    "aphrodize_http_duration_seconds",
    "API response duration",
    ["method", "route"],
    registry=registry,
)
jobs = Counter(
    "aphrodize_jobs_total", "Finished job attempts", ["function", "outcome"], registry=registry
)
secondary_failures = Counter(
    "aphrodize_secondary_failures_total",
    "Failure of retention/review side effects",
    ["operation"],
    registry=registry,
)
for operation in ("incomplete_artifact_cleanup", "source_cleanup", "annotation_staging"):
    secondary_failures.labels(operation)
job_duration = Histogram(
    "aphrodize_job_duration_seconds",
    "Job processing duration",
    ["function"],
    buckets=(1, 5, 15, 30, 60, 120, 300, 900, 3600),
    registry=registry,
)
queue_wait = Histogram(
    "aphrodize_job_queue_wait_seconds",
    "Time after job becomes due",
    ["function"],
    buckets=(1, 5, 15, 30, 60, 120, 300, 900),
    registry=registry,
)
dependency_up = Gauge(
    "aphrodize_dependency_up", "Dependency check succeeded", ["dependency"], registry=registry
)
dependency_required = Gauge(
    "aphrodize_dependency_required",
    "Dependency expected for deployment",
    ["dependency"],
    registry=registry,
)
worker_up = Gauge("aphrodize_worker_up", "ARQ heartbeat key present", ["queue"], registry=registry)
queued = Gauge(
    "aphrodize_queued_jobs",
    "Persisted main workflow rows waiting for execution",
    ["queue"],
    registry=registry,
)
oldest = Gauge(
    "aphrodize_queue_oldest_seconds",
    "Oldest queued main workflow row age",
    ["queue"],
    registry=registry,
)
running_age = Gauge(
    "aphrodize_running_oldest_seconds",
    "Oldest running row age since creation",
    ["queue"],
    registry=registry,
)
collector_success = Gauge(
    "aphrodize_collector_success", "Last collection succeeded", registry=registry
)
collector_at = Gauge(
    "aphrodize_collector_timestamp_seconds", "Last collection attempt", registry=registry
)
uv_up = Gauge(
    "aphrodize_uv_forecast_ready", "Forecast usable for required dates", registry=registry
)
uv_generated = Gauge(
    "aphrodize_uv_generated_timestamp_seconds", "UV snapshot publication time", registry=registry
)
uv_quality = Gauge(
    "aphrodize_uv_quality_ready", "UV quality report fresh and not alerting", registry=registry
)
uv_enabled = Gauge(
    "aphrodize_uv_monitoring_enabled", "UV expected for deployment", registry=registry
)


def valid_request_id(value: str | None) -> str:
    # Bound client input; UUID-shaped correlation IDs contain no free-form PII.
    return value.lower() if value and re.fullmatch(r"[0-9a-fA-F]{32}", value) else uuid4().hex


class SafeJsonFormatter(logging.Formatter):
    def format(self, record):
        value = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "service": os.getenv("SERVICE_NAME", "api"),
            "environment": os.getenv("APP_ENV", "development"),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", "application_log"),
            "logger": record.name,
            "location": f"{record.funcName}:{record.lineno}",
            "request_id": request_id.get(),
            "job_id": job_id.get(),
        }
        # Do not serialize message/args, exception messages, SQL, headers or locals.
        for key in ("route", "method", "status", "duration_seconds", "function", "outcome"):
            if hasattr(record, key):
                value[key] = getattr(record, key)
        if record.exc_info:
            value["error_type"] = record.exc_info[0].__name__
            value["frames"] = [
                f"{f.name}:{f.lineno}" for f in traceback.extract_tb(record.exc_info[2])[-8:]
            ]
        return json.dumps(value, separators=(",", ":"))


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "arq"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


class ObserveHTTP:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        correlation = valid_request_id(headers.get(b"x-request-id", b"").decode("ascii", "ignore"))
        token = request_id.set(correlation)
        started, status = time.monotonic(), 500

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"
                ]
                message["headers"].append((b"x-request-id", correlation.encode()))
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except Exception:
            logging.getLogger(__name__).exception("", extra={"event": "http_exception"})
            raise
        finally:
            # Router resolves the template after dispatch; unknown paths share one label.
            route = getattr(scope.get("route"), "path", "unmatched")
            method = (
                scope["method"]
                if scope["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
                else "OTHER"
            )
            duration = time.monotonic() - started
            if route not in {"/api/v1/health", "/api/v1/monitoring/metrics"}:
                http_requests.labels(method, route, str(status)).inc()
                http_duration.labels(method, route).observe(duration)
                logging.getLogger(__name__).info(
                    "",
                    extra={
                        "event": "http_completed",
                        "route": route,
                        "method": method,
                        "status": status,
                        "duration_seconds": duration,
                    },
                )
            request_id.reset(token)


async def enqueue_job(redis, function, *args, **kwargs):
    if request_id.get():
        kwargs["_request_id"] = request_id.get()
    result = await redis.enqueue_job(function, *args, **kwargs)
    if result is not None:
        token = job_id.set(str(getattr(result, "job_id", "")))
        try:
            logging.getLogger(__name__).info(
                "", extra={"event": "job_enqueued", "function": function}
            )
        finally:
            job_id.reset(token)
    return result


def observed_job(function):
    for outcome in ("succeeded", "failed", "rejected", "skipped", "cancelled"):
        jobs.labels(function.__name__, outcome)

    @functools.wraps(function)
    async def run(ctx, *args, _request_id=None, **kwargs):
        correlation = request_id.set(valid_request_id(_request_id))
        identifier = job_id.set(str(ctx.get("job_id", "")))
        started = time.monotonic()
        score = ctx.get("score")
        if score is not None:
            queue_wait.labels(function.__name__).observe(max(0, time.time() - score / 1000))
        outcome = "failed"
        logging.getLogger(__name__).info(
            "", extra={"event": "job_started", "function": function.__name__}
        )
        try:
            result = await function(ctx, *args, **kwargs)
            outcome = ctx.pop("telemetry_outcome", "succeeded")
            if outcome not in {"succeeded", "failed", "rejected", "skipped"}:
                outcome = "failed"
            return result
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception:
            logging.getLogger(__name__).exception(
                "", extra={"event": "job_exception", "function": function.__name__}
            )
            raise
        finally:
            duration = time.monotonic() - started
            jobs.labels(function.__name__, outcome).inc()
            job_duration.labels(function.__name__).observe(duration)
            logging.getLogger(__name__).info(
                "",
                extra={
                    "event": "job_finished",
                    "function": function.__name__,
                    "outcome": outcome,
                    "duration_seconds": duration,
                },
            )
            job_id.reset(identifier)
            request_id.reset(correlation)

    return run


async def start_worker_metrics(ctx):
    configure_logging()
    try:
        port = int(os.getenv("WORKER_METRICS_PORT", "0"))
        if port:
            ctx["metrics_server"] = start_http_server(port, registry=registry)
    except (ValueError, OSError):
        logging.getLogger(__name__).exception("", extra={"event": "metrics_listener_failed"})


async def stop_worker_metrics(ctx):
    if server := ctx.pop("metrics_server", None):
        await asyncio.to_thread(server[0].shutdown)
        server[0].server_close()
