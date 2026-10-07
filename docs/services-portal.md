# Services portal

Open `https://aphrodize.duckdns.org/portal` directly. The portal has no entry
in the shared navigation, and the portal page has no navbar. Label Studio, Grafana and Product admin keep their own sign-in flows.
MinIO Console has no public entry yet. The portal shows it as unavailable until
`PORTAL_MINIO_URL` is configured. Its S3 API stays private.

`docker/Caddyfile.minio-console.example` contains a proposed route for
`https://minio.aphrodize.duckdns.org`, proxying the Console on port 9001. This is
not loaded by Caddy. Enabling it exposes the existing MinIO administrator login
to the internet and requires operator approval. After approval, add the route
to the DuckDNS Caddyfile, validate and reload Caddy, then set `PORTAL_MINIO_URL`
and recreate the frontend. DNS resolution and a certificate for the Console
hostname are required.

The portal lists infrastructure without a browser UI separately. It does not
probe health or label services healthy. Missing Console/MLflow URLs render as
unavailable text, never as a link to localhost on the visitor's computer.

MLflow is not running on the current VM. After deploying an authenticated MLflow
endpoint, set server-only `PORTAL_MLFLOW_URL` and recreate the frontend.
The portal never carries service passwords or API tokens.

For local development, configure `PORTAL_MINIO_URL=http://localhost:9001` and
`PORTAL_MLFLOW_URL=http://localhost:5000` in the frontend environment when those
services are running. The Label Studio and Grafana links use the VM proxy paths.
