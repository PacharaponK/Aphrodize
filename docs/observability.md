# Observability and application releases

The VM serves Grafana at `https://<VM_HOST>/grafana/` through the existing Caddy
HTTPS origin. API metrics/readiness use service Basic authentication; Grafana has
its own account. Anonymous access and signup are disabled. Metrics and logs exclude
private payloads, credentials, cookies, raw URLs, SQL and exception messages.

## VM configuration

Keep the deployment's `.env` private. Copy settings from
`docker/observability/.env.example`, generate a unique Grafana password, and enable
the services actually present. The current deployment uses:

```dotenv
OBS_GRAFANA_USER=admin
OBS_GRAFANA_PASSWORD=<unique private password>
OBS_EXPECTED_QUEUES=
OBS_MINIO_REQUIRED=true
OBS_UV_ENABLED=true
OBS_CADDY_ENABLED=true
OBS_FRONTEND_ENABLED=true
```

Render private scrape credentials and targets from the same `.env` used by Compose:

```bash
uv run --locked python scripts/configure_observability.py --env-file .env
docker compose --env-file .env -f compose.vm.yml -f compose.vm-worker-access.yml -f compose.duckdns.yml -f compose.observability.yml -f compose.observability-web.yml config --quiet
```

Initial monitoring installation is a separate VM maintenance operation. The optional
monitoring services must already be running before application releases use their
overlays. Start them with the same Compose files and project directory as the VM.
Keep Prometheus (9090), Loki (3100) and Grafana's direct port (3001) on host loopback;
only Caddy exposes Grafana through authenticated HTTPS. Campus/VPN routing still applies.
Do not print resolved Compose configuration because it contains secrets.

## CI/CD preservation

After integrating the compatible deployer into `main`, configure the repository variable:

```text
VM_COMPOSE_OVERLAYS=compose.vm-worker-access.yml,compose.duckdns.yml,compose.observability.yml,compose.observability-web.yml
```

The deployer reads the VM's existing overlays and private configuration. It updates
only API/frontend, preserving running monitoring containers, volumes, provisioning
and Grafana accounts. Preflight rejects changes to existing monitoring infrastructure
or disabling API telemetry. Existing annotation environment settings are preserved.

The published API image is smoke-tested for the metrics route and collector metrics.
Post-deploy checks require authenticated metrics from a successful collector within
120 seconds and the Grafana HTTPS health endpoint. Brief retries tolerate startup
and an older rollback image's collection cycle. Failure restores the previous
application configuration without restarting monitoring or deleting volumes.
Recovery/manual rollback use the same checks and preserve prior release history.

## Browser operation

Open `/grafana/`, sign in with the deployment's private Grafana account, and select
Dashboards → Aphrodize. System shows API/web probes, dependencies, CPU/RAM/disk,
latency and safe logs. UV shows forecast/quality readiness and snapshot freshness.
Jobs includes worker/GPU panels, but those remain without live data in this integration.
This release does not change queued job arguments or activate worker/GPU telemetry.

In Explore select Loki and use `{service="api"} | json`; add `| level="error"`
to filter errors. Alert rules evaluate in Grafana. Discord delivery remains unconfigured
until a private webhook is provided and separately verified. Monitoring on the same
VM cannot notify when the entire VM loses power/network; no external probe is running.

Metrics retain 15 days with a 2 GB cap, logs retain 7 days, and named volumes preserve
state through restarts. Loki time retention is not a hard disk quota. The monitoring
stack's configured memory limits total roughly 2 GB; measure actual VM headroom.

## Checks

```bash
uv run --locked python -m pytest tests/test_observability.py tests/test_observability_readiness.py tests/test_vm_deployment.py
python scripts/check_observability_web.py --url https://<VM_HOST>/grafana/
```

Deployment regression tests use disposable fake Docker/curl binaries on Linux and
exercise success, preflight rejection, health failure, rollback and recovery. They
do not stop production services. Re-render targets and restart Prometheus separately
after changing API credentials or target settings.
