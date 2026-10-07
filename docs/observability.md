# Observability operations

The optional stack adds Prometheus, Loki, Alloy, Grafana Alerting (Discord), host metrics,
HTTP probes and optional GPU metrics. The application keeps Docker's local log driver.
Default application startup does not depend on these services. No private image, health
payload, cookie, authorization header, raw URL/query, SQL or exception message belongs in
telemetry. Request/job IDs are correlation metadata, not metric labels.

## Deployment configuration

Copy the settings from `docker/observability/.env.example` into the deployment's private
`.env`. Generate a unique `OBS_GRAFANA_PASSWORD`. Put the Discord channel webhook in
`DISCORD_WEBHOOK_URL` **in the private file**, never in Git or chat. Grafana uses the native
[Discord contact point](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-discord/).
Until a webhook is supplied, the contact points intentionally fail against local loopback;
dashboard/alert evaluation works but recipient delivery is unverified.

Set deployment features explicitly:

| Setting | VM without workers | Local AI stack | VM with GPU worker |
| --- | --- | --- | --- |
| `OBS_EXPECTED_QUEUES` | empty | `inference,training` | `inference` |
| `OBS_MINIO_REQUIRED` | `true` | `true` | `true` |
| `OBS_UV_ENABLED` | `true` if UV snapshots are served | depends on workload | depends on workload |
| `OBS_CADDY_ENABLED` | `true` | `false` | `true` |
| `OBS_FRONTEND_ENABLED` | `true` | `false` unless frontend joins Compose | `true` |

For a minimal local stack without MinIO, set `OBS_MINIO_REQUIRED=false` and disable UV,
Caddy and frontend flags unless present. Expected-but-stopped workers should alert; an
intentionally disabled worker should not. Worker target files are generated only for expected
queues. GPU/DCGM targets are opt-in. Caddy's private port 9100 exposes metrics without
opening its administration API.

Render scrape configuration from the same environment file used by Compose:

```powershell
uv run --locked python scripts/configure_observability.py --env-file .env
docker compose --env-file .env -f compose.vm.yml -f compose.observability.yml config --quiet
docker compose --env-file .env -f compose.vm.yml -f compose.observability.yml up -d --build
```

If using release or DuckDNS overlays, keep them in the same Compose command, in the existing
order, then add the observability overlay. Release image digests must contain this code;
adding the overlay to an old API image does not implement instrumentation. Re-render and
restart Prometheus after changing API credentials/targets. The rendered `.observability/`
directory is ignored by Git. Its directory is mode 0700 on Linux; the mounted password file
must be readable by Prometheus's container user. Protect the equivalent Windows directory
with the owner's ACL. Do not print rendered Compose config containing environment secrets.

For the local AI stack:

```powershell
docker compose --profile ai --profile background -f compose.yml -f compose.observability.yml -f compose.observability-workers.yml up -d --build
```

Deploy updated workers **before** updated API producers: older workers do not accept the
new correlation metadata. Cron and old queued jobs without metadata remain supported.
Each instrumented worker exposes port 9101 only internally, and uses ARQ's native Redis
health key every 30 seconds. For scale-out, assign distinct worker targets/heartbeat keys;
the current heartbeat represents one worker pool per queue, not every replica.

## Access and budgets

Use `ssh -N -L 3001:127.0.0.1:3001 operator@vm` and open
`http://localhost:3001` to log in to Grafana. Prometheus (9090) and Loki (3100) bind to
host loopback for administration/tunnels. No unauthenticated monitoring port should be
published to the internet. Grafana anonymous access and signup are disabled. API metrics
and readiness use the existing service Basic authentication.

Metrics retain 15 days with a 2 GB TSDB cap; Loki retains 7 days. Persistent named volumes
retain dashboards/state through restarts. Loki ingestion is limited to 2 MB/s, with a 64 MB
embedded cache. The stack's memory limits total about 2 GB; measure actual headroom before
deploying alongside inference. Docker Desktop host metrics describe its Linux VM, not the
Windows machine. Loki has time retention, **not a hard disk quota**: budget a dedicated
filesystem/quota for logs and monitor that filesystem. Never delete application or database
volumes to clear a monitoring alert. Retention deletes are asynchronous.

The Docker socket proxy accepts GET container/network metadata and logs, and denies POST. It is reachable
only by Alloy on an internal collector network; no Docker socket is mounted in Alloy. GET
access still reveals container metadata, so restrict access to both services. Alloy collects
only the configured Compose project and instrumented application services, drops non-JSON
library records, and reconstructs allowlisted fields before sending logs to Loki.

## GPU worker on another machine

Merge `compose.gpu.yml` with `compose.gpu-observability.yml`, using the existing private
`.env.gpu`. Enable profile `gpu-metrics` only after NVIDIA toolkit/DCGM preflight passes.
The existing inference `restart: no` safety rule is preserved. Set `LOKI_URL` for GPU Alloy;
keep all communication inside private SSH tunnels or an authenticated TLS network.

One Linux tunnel arrangement (replace addresses/user; use approved SSH keys):

1. On the VM, find Docker's host gateway with
   `docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'`.
   Bind SSH's local forwards to **that gateway only**:
   `ssh -N -L <VM_DOCKER_GATEWAY>:19101:127.0.0.1:9101 -L <VM_DOCKER_GATEWAY>:19400:127.0.0.1:9400 operator@gpu`.
   Firewall these listeners to the monitoring network.
2. Set `OBS_INFERENCE_TARGET=host.docker.internal:19101` and, if DCGM is enabled,
   `OBS_GPU_TARGET=host.docker.internal:19400` on the VM; re-render and restart Prometheus.
3. On the GPU host, create the opposite outbound tunnel:
   `ssh -N -L <GPU_DOCKER_GATEWAY>:13100:127.0.0.1:3100 operator@vm`.
   Set `LOKI_URL=http://host.docker.internal:13100/loki/api/v1/push` in `.env.gpu`.
   Firewall this listener to GPU Alloy. Supervise the SSH processes; tunnel loss should
   produce exporter/heartbeat or log-delivery alerts.

No SSH credentials or GPU access are provisioned automatically. If Docker has a customized
host-gateway address, use that actual address consistently for both listener and target.

## Semantics and dashboards

`/api/v1/health` is liveness only. `/api/v1/monitoring/ready` checks `SELECT 1`, Redis PING,
and authenticated MinIO bucket existence with short timeouts. It returns capabilities and
dependency status, with HTTP 503 when account/database service is unavailable. Storage/queue
failure yields `degraded` while account service remains available. Job submission readiness
does not prove that a worker/model is ready; consult the expected worker heartbeat metrics.
Readiness is independent of Prometheus/Grafana.

| Dashboard | What to inspect |
| --- | --- |
| System | API/frontend probes, route metrics, dependency checks, CPU/RAM/disk, telemetry freshness |
| Jobs | Expected heartbeat, queued main workflow rows, wait/processing p95, outcomes, GPU memory |
| UV | Forecast usability, snapshot age, quality report freshness/alerts |

Queue gauges aggregate `queued` rows from Analysis, InferenceRun and TrainingRun without
fetching payloads. They detect persisted orphaned rows even if the Redis job disappeared.
Deferred cleanup/annotation jobs and the cohort-training singleton are not included in these
gauges; they still emit job metrics/logs when run. Running-row age starts at submission,
because the current schema has no execution-start timestamp. Processing histograms measure
actual execution separately. Add indexed status/creation queries if collection exceeds its
3-second timeout at larger volumes.

Job `failed` is separate from image `rejected`; swallowed business failures explicitly mark
the job outcome. Job counters measure attempts, including retries/cancellations, not unique
user analyses. UV freshness reuses the existing validated snapshot and monitoring report;
disabled UV monitoring suppresses its alerts. Model quality reporting remains in MLflow and
existing monitoring APIs; operational telemetry does not validate model accuracy.

In Grafana Explore select Loki and query:

```text
{service=~"api|frontend|inference-worker|trainer-worker"} | json | request_id="<32-hex-id>"
```

Find `job_enqueued`, then follow `job_id` to `job_started`/`job_finished`. Exception logs keep
type and safe code locations while discarding messages, SQL parameters and locals.

## Alerts and response

Rules are provisioned from `docker/observability/grafana/alerting/rules.yml`. Edit pilot
thresholds in `scripts/generate_observability_dashboards.py`, then run that script to regenerate
dashboards/rules and restart Grafana. Provisioned resources are deliberately read-only in UI.

| Alert | Pilot threshold | Response and recovery check |
| --- | --- | --- |
| API/probe down | 2 minutes | Check process/network, then verify liveness and readiness |
| Required dependency down | 2 minutes | Inspect named service/auth; recover without removing volumes |
| Expected worker/exporter missing | 2 minutes | Check process, Redis, private tunnel, reviewed model configuration |
| Inference queue stuck | oldest queued >5 minutes, held 2 minutes | Find job logs; reconcile DB/Redis before any retry |
| Training queue stuck | oldest queued >1 hour, held 5 minutes | Check trainer and workload duration |
| Inference running overdue | row age >15 minutes, held 2 minutes | Distinguish long queue wait from execution; reconcile crash state |
| Retention/annotation staging failed | any failure in 5 minutes | Inspect named operation; reconcile artifacts or annotation staging even if inference succeeded |
| API/frontend errors | >5% 5xx with ≥20 requests in 5 minutes, held 5 minutes | Identify route/request, recover upstream and verify error rate drops |
| Disk low | <15% free for 10 minutes | Check log/artifact growth and approved retention; verify headroom |
| Collector failing/stale | failure or >120 seconds stale, held 2 minutes | Check `collector_failed`, SQL/Redis; confirm timestamp advances |
| UV unavailable/stale | >8 hours or invalid dates, held 5 minutes | Inspect refresh logs, snapshot and serving pointer |
| UV quality attention | stale/missing/alert quality report, held 5 minutes | Inspect monitoring report; preserve manual model approval |

Notifications group by alert/dependency/queue, wait 30 seconds, group updates every 5 minutes,
and repeat unresolved alerts every 4 hours. Discord receives firing and resolved messages with
dashboard links and response hints. Set `OBS_GRAFANA_URL` to the URL operators can actually
access; links to localhost require the operator's SSH tunnel. Use Grafana Contact points →
operations → Test to verify **the actual channel**, then perform a controlled staging fault
and recovery drill. Merely saving a webhook does not verify delivery.

## Independent probe limitation

There is currently **no independent machine** for the external probe. Monitoring on the VM
cannot send an alert when the entire VM/network/power fails. This remains an operational gap.
When another host/provider is available, run `compose.external-probe.yml` there with
`PROBE_URL=https://<domain>/api/health` and its Discord webhook. It verifies HTTPS and JSON
liveness, persists state, sends one outage/recovery transition and retries failed deliveries.
Four failed 30-second probes represent about two minutes. This probes frontend liveness;
internal API probes/dependency alerts cover backend failures. It is not a synthetic login or
image-inference test. Protect the probe's webhook file and supervise the probe itself.

## Verification and rollback

```powershell
uv run --locked python -m pytest tests/test_observability.py
uv run --locked python -m scripts.test_observability_stack
.\scripts\check-health.ps1 -ComposeFiles compose.vm.yml,compose.observability.yml
```

The Docker check creates only `aphrodize-observability-check`, uses synthetic metrics and a
local Discord-compatible receiver, verifies Grafana provisioning, Prometheus scrape,
Docker local-driver → Alloy → Loki privacy filtering, firing/recovery delivery and restart
persistence, then removes that test project's disposable containers/volumes. It does not
test production GPU hardware, real Discord, or actual VM reachability.

In staging also stop a worker, interrupt Redis, make a UV snapshot stale, stop Alloy, and
confirm matching alerts and resolved notifications. Never perform these drills against live
user workloads without scheduling the interruption. Observe baseline for seven days before
setting production latency/availability objectives. The seven-day baseline cannot be claimed
from a development run.

To disable collection, set `OBSERVABILITY_ENABLED=false` and stop only the monitoring
services. Keep monitoring volumes if history is needed. Restore the prior application images
if rolling back instrumentation; do not remove PostgreSQL, Redis or MinIO data. No distributed
tracing store is deployed in this first version; correlation IDs already connect the critical
request/job flow and can later become trace context when needed.
