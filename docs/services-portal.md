# Services portal

Open `https://aphrodize.duckdns.org/portal` directly and sign into the app if prompted. The portal remains a standalone page without the shared navbar. External tools open in a new tab.

| Service | Entrance | Sign-in |
| --- | --- | --- |
| Aphrodize | `https://aphrodize.duckdns.org/` | App account |
| Label Studio | `https://aphrodize.duckdns.org/label-studio/` | Label Studio account |
| MinIO Console | `https://minio.aphrodize.duckdns.org/` | Existing MinIO account |
| MLflow | `https://mlflow.aphrodize.duckdns.org/` | Existing Product admin account at the HTTPS gateway |
| Grafana | `https://aphrodize.duckdns.org/grafana/` | Grafana account |
| Prometheus | `https://prometheus.aphrodize.duckdns.org/` | Existing Product admin account at the HTTPS gateway |
| Product admin | `https://aphrodize.duckdns.org/admin` | Product admin account |

## Deployment

Merge `compose.services-portal.yml` after the existing VM, DuckDNS, and observability configurations. Caddy needs `ADMIN_USERNAME` and a bcrypt `PORTAL_OPERATOR_PASSWORD_HASH` generated from the existing admin password using `caddy hash-password`. Never save plaintext passwords into a new release file or commit them. Use `--env-file .env` explicitly when the first Compose file lives under `.releases/`.

The DuckDNS Caddyfile routes the three service subdomains with one wildcard DNS-01 HTTPS certificate, avoiding concurrent DuckDNS TXT challenges. Unknown subdomains return 404. MinIO Console retains its own authentication. MLflow and Prometheus require authentication at Caddy; Caddy removes the gateway Authorization header before proxying. Their ports are not published publicly. DNS must resolve each hostname to the VM.

MLflow stores experiment metadata in the `mlflow` PostgreSQL database and proxies artifact access into the private MinIO `mlflow` bucket. On an existing VM, create that database once with the existing PostgreSQL operator; existing volumes do not rerun initialization scripts. Build `docker/mlflow.Dockerfile` against the deployed API image. The start script enables server artifact proxying so browser clients do not need direct S3 access.

The overlay sets server-only `PORTAL_MINIO_URL`, `PORTAL_MLFLOW_URL`, and `PORTAL_PROMETHEUS_URL`. Missing or invalid URLs still render unavailable text. The portal never carries passwords, tokens, or inferred service health.

PostgreSQL, Redis and the MinIO S3 API remain accessible through VM loopback/SSH. Loki, Alloy, exporters, API, workers and Caddy can be inspected through Grafana; the portal lists these separately with their connection guidance.

For local development, optional service URLs may point to localhost only when those services run on the visitor's computer.
