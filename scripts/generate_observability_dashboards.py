"""Generate provisioned dashboards and alerts; thresholds are pilot defaults."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "docker/observability/grafana"


def dashboard(uid, title, panels):
    result = {
        "uid": uid,
        "title": title,
        "schemaVersion": 39,
        "version": 1,
        "editable": False,
        "tags": ["aphrodize"],
        "timezone": "browser",
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "30s",
        "panels": [],
    }
    for i, (name, query, unit) in enumerate(panels):
        result["panels"].append(
            {
                "id": i + 1,
                "title": name,
                "type": "timeseries",
                "gridPos": {"x": (i % 2) * 12, "y": (i // 2) * 8, "w": 12, "h": 8},
                "datasource": {"type": "prometheus", "uid": "prometheus"},
                "targets": [
                    {
                        "refId": "A",
                        "expr": query,
                        "legendFormat": "{{instance}} {{queue}} {{dependency}}",
                    }
                ],
                "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
            }
        )
    if uid != "aphrodize-uv":
        result["panels"].append(
            {
                "id": 100,
                "title": "Logs — filter request_id/job_id in Explore",
                "type": "logs",
                "gridPos": {"x": 0, "y": ((len(panels) + 1) // 2) * 8, "w": 24, "h": 10},
                "datasource": {"type": "loki", "uid": "loki"},
                "targets": [
                    {
                        "refId": "A",
                        "expr": '{service=~"api|frontend|inference-worker|trainer-worker"} | json',
                    }
                ],
            }
        )
    return result


DASHBOARDS = [
    (
        "aphrodize-system",
        "Aphrodize — System",
        [
            ("Scrape targets", "up", "short"),
            ("HTTP probes", "probe_success", "short"),
            ("API request rate", "sum(rate(aphrodize_http_requests_total[5m]))", "reqps"),
            (
                "API 5xx ratio",
                'sum(rate(aphrodize_http_requests_total{status=~"5.."}[5m])) / cla'
                "mp_min(sum(rate(aphrodize_http_requests_total[5m])), 0.001)",
                "percentunit",
            ),
            (
                "API p95",
                "histogram_quantile(0.95, sum by(le) (rate(aphrodize_http_duration"
                "_seconds_bucket[5m])))",
                "s",
            ),
            ("Dependencies", "aphrodize_dependency_up", "short"),
            ("CPU usage", '1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))', "percentunit"),
            (
                "RAM usage",
                "1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes",
                "percentunit",
            ),
            (
                "Disk free",
                'node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes',
                "percentunit",
            ),
            (
                "Frontend through Caddy p95",
                "histogram_quantile(0.95, sum by(le) (rate(caddy_http_request_dura"
                'tion_seconds_bucket{handler="reverse_proxy"}[5m])))',
                "s",
            ),
            ("Collector freshness", "time() - aphrodize_collector_timestamp_seconds", "s"),
            ("Loki disk bytes", 'node_filesystem_avail_bytes{mountpoint="/"}', "bytes"),
        ],
    ),
    (
        "aphrodize-jobs",
        "Aphrodize — Jobs",
        [
            ("Worker heartbeat", "aphrodize_worker_up", "short"),
            ("Queued main jobs", "aphrodize_queued_jobs", "short"),
            ("Oldest queue wait", "aphrodize_queue_oldest_seconds", "s"),
            ("Oldest running row (since submission)", "aphrodize_running_oldest_seconds", "s"),
            ("Job outcomes", "sum by(function,outcome) (rate(aphrodize_jobs_total[5m]))", "ops"),
            (
                "Retention/review failures",
                "sum by(operation) (increase(aphrodize_secondary_failures_total[5m]))",
                "short",
            ),
            (
                "Processing p95",
                "histogram_quantile(0.95, sum by(le,function) (rate(aphrodize_job_"
                "duration_seconds_bucket[5m])))",
                "s",
            ),
            (
                "Queue wait p95",
                "histogram_quantile(0.95, sum by(le,function) (rate(aphrodize_job_"
                "queue_wait_seconds_bucket[5m])))",
                "s",
            ),
            ("GPU memory used", "DCGM_FI_DEV_FB_USED * 1024 * 1024", "bytes"),
        ],
    ),
    (
        "aphrodize-uv",
        "Aphrodize — UV",
        [
            ("Forecast ready", "aphrodize_uv_forecast_ready", "short"),
            ("Snapshot age", "time() - aphrodize_uv_generated_timestamp_seconds", "s"),
            ("Quality report fresh and healthy", "aphrodize_uv_quality_ready", "short"),
        ],
    ),
]

# Each query emits 0/1 with original labels; optional targets use NoData=OK.
ALERTS = [
    (
        "secondary-failed",
        "Retention or annotation staging failed",
        "sum by(operation) (increase(aphrodize_secondary_failures_total[5m])) > bool 0",
        "0s",
        "warning",
        "jobs",
        "Inspect the named operation and reconcile retained artifacts or annotation staging.",
    ),
    (
        "api-down",
        "API scrape unavailable",
        '1 - (up{job="api"} or on() vector(0))',
        "2m",
        "critical",
        "system",
        "Check API process, scrape credentials and network.",
    ),
    (
        "probe-down",
        "HTTP probe failed",
        "1 - probe_success",
        "2m",
        "critical",
        "system",
        "Check frontend/API routing and dependency readiness.",
    ),
    (
        "dependency-down",
        "Required dependency unavailable",
        "(aphrodize_dependency_up == bool 0) * on(dependency) aphrodize_dependency_required",
        "2m",
        "critical",
        "system",
        "Check the named dependency; preserve volumes while recovering.",
    ),
    (
        "worker-down",
        "Expected worker heartbeat missing",
        "1 - aphrodize_worker_up",
        "2m",
        "critical",
        "jobs",
        "Check worker process, Redis connectivity and approved model readiness.",
    ),
    (
        "queue-stuck",
        "Inference queue waiting too long",
        'aphrodize_queue_oldest_seconds{queue="inference"} > bool 300',
        "2m",
        "warning",
        "jobs",
        "Check worker heartbeat and processing errors. Do not discard queued jobs.",
    ),
    (
        "training-stuck",
        "Training queue waiting too long",
        'aphrodize_queue_oldest_seconds{queue="training"} > bool 3600',
        "5m",
        "warning",
        "jobs",
        "Check trainer availability and training schedule.",
    ),
    (
        "running-stuck",
        "Inference running row overdue",
        'aphrodize_running_oldest_seconds{queue="inference"} > bool 900',
        "2m",
        "warning",
        "jobs",
        "Inspect job logs; age is since submission, not execution start. R"
        "econcile state before retrying.",
    ),
    (
        "api-errors",
        "API 5xx rate elevated",
        '(sum(rate(aphrodize_http_requests_total{status=~"5.."}[5m])) / cl'
        "amp_min(sum(rate(aphrodize_http_requests_total[5m])), 0.001) > bo"
        "ol 0.05) * (sum(increase(aphrodize_http_requests_total[5m])) >= b"
        "ool 20)",
        "5m",
        "warning",
        "system",
        "Find failing routes and request IDs in logs.",
    ),
    (
        "frontend-errors",
        "Frontend 5xx rate elevated",
        '(sum(rate(caddy_http_request_duration_seconds_count{handler="reve'
        'rse_proxy",code=~"5.."}[5m])) / clamp_min(sum(rate(caddy_http_req'
        'uest_duration_seconds_count{handler="reverse_proxy"}[5m])), 0.001'
        ") > bool 0.05) * (sum(increase(caddy_http_request_duration_second"
        's_count{handler="reverse_proxy"}[5m])) >= bool 20)',
        "5m",
        "warning",
        "system",
        "Inspect frontend backend_request and request_error logs.",
    ),
    (
        "disk-low",
        "Host disk below 15 percent",
        '(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_file'
        "system_size_bytes < bool 0.15) * on(instance,device,mountpoint) ("
        "node_filesystem_readonly == bool 0)",
        "10m",
        "warning",
        "system",
        "Check log and artifact usage; follow retention policy before deleting data.",
    ),
    (
        "collector-failed",
        "Operational collector failing",
        "clamp_max((aphrodize_collector_success == bool 0) + (time() - aph"
        "rodize_collector_timestamp_seconds > bool 120), 1)",
        "2m",
        "warning",
        "system",
        "Inspect collector_failed events and SQL/Redis connectivity.",
    ),
    (
        "optional-scrape",
        "Configured exporter unavailable",
        'up{job=~"optional-workers|optional-gpu|optional-caddy|node|loki|alloy"} == bool 0',
        "2m",
        "warning",
        "system",
        "Check exporter process, private tunnels and target configuration.",
    ),
    (
        "uv-stale",
        "UV forecast unavailable or stale",
        "(aphrodize_uv_forecast_ready == bool 0) * aphrodize_uv_monitoring_enabled",
        "5m",
        "warning",
        "uv",
        "Inspect uv-refresh; validate snapshot and serving-version pointer.",
    ),
    (
        "uv-quality",
        "UV quality monitoring requires attention",
        "(aphrodize_uv_quality_ready == bool 0) * aphrodize_uv_monitoring_enabled",
        "5m",
        "warning",
        "uv",
        "Inspect monitoring.json and UV quality gate. Do not auto-promote a model.",
    ),
]


def alert_rule(item):
    uid, title, expr, duration, severity, page, summary = item
    return {
        "uid": uid,
        "title": title,
        "condition": "C",
        "for": duration,
        "noDataState": "OK",
        "execErrState": "Alerting",
        "isPaused": False,
        "labels": {"severity": severity},
        "annotations": {
            "summary": summary,
            "__dashboardUid__": f"aphrodize-{page}",
            "__panelId__": "1",
            "runbook": "docs/observability.md",
        },
        "data": [
            {
                "refId": "A",
                "relativeTimeRange": {"from": 300, "to": 0},
                "datasourceUid": "prometheus",
                "model": {
                    "refId": "A",
                    "expr": expr,
                    "instant": True,
                    "intervalMs": 1000,
                    "maxDataPoints": 43200,
                },
            },
            {
                "refId": "C",
                "relativeTimeRange": {"from": 0, "to": 0},
                "datasourceUid": "__expr__",
                "model": {
                    "refId": "C",
                    "type": "threshold",
                    "expression": "A",
                    "conditions": [
                        {
                            "evaluator": {"type": "gt", "params": [0]},
                            "operator": {"type": "and"},
                            "query": {"params": ["C"]},
                            "reducer": {"type": "last", "params": []},
                            "type": "query",
                        }
                    ],
                },
            },
        ],
    }


def main():
    for uid, title, panels in DASHBOARDS:
        (ROOT / "dashboards" / f"{uid}.json").write_text(
            json.dumps(dashboard(uid, title, panels), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    rules = {
        "apiVersion": 1,
        "groups": [
            {
                "orgId": 1,
                "name": "operations",
                "folder": "Aphrodize",
                "interval": "30s",
                "rules": [alert_rule(a) for a in ALERTS],
            }
        ],
    }
    (ROOT / "alerting/rules.yml").write_text(
        yaml.safe_dump(rules, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
