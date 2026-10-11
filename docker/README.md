# Container and deployment configuration

Build contexts are the repository root. Start with [root setup](../README.md); do not build these Dockerfiles from inside `docker/`.

## Images

| Dockerfile | Purpose |
| --- | --- |
| `api.Dockerfile` | Locked Python 3.11 API environment and baseline model |
| `inference.Dockerfile` | CPU PyTorch wrinkle worker and MediaPipe asset |
| `inference-cuda.Dockerfile` | CUDA inference worker; requires GPU deployment setup |
| `trainer.Dockerfile` | Controlled training worker |
| `frontend.Dockerfile` | Node.js 24 / pnpm 11.19.0 production frontend; lint/type/build checks |
| `mlflow.Dockerfile` | MLflow using the API image as an additional build context |
| `minio.Dockerfile` | Locally built MinIO image |
| `caddy-duckdns.Dockerfile` | Caddy build for the documented DuckDNS setup |

Inference builds download packages and a face-landmarker asset. Runtime wrinkle checkpoints remain external under `storage/models/ffhq-wrinkle/`. Mounting an empty directory does not install models.

## Compose selection

| Root file | Use |
| --- | --- |
| `compose.yml` | Development API/database/Redis; `ai`, `demo`, `background`, and `uv-training` profiles |
| `compose.vm.yml` | VM web/API/storage stack and HTTPS proxy; separate deployment variables required |
| `compose.gpu.yml`, `compose.wrinkle-gpu.yml` | GPU deployment configurations; use the GPU guide's file selection |
| `compose.release.yml` | Release configuration; use CI/CD release instructions |
| `compose.observability*.yml`, `compose.gpu-observability.yml` | Optional monitoring configurations for documented topologies |
| `compose.duckdns.yml`, `compose.vm-worker-access.yml`, `compose.external-probe.yml` | Specialized DNS, worker access, and external-probe configurations |

These files are not interchangeable. Use the exact `-f` combination and environment specified in [VM deployment](../docs/deploy-vm.md), [GPU deployment](../docs/deploy-gpu.md), [CI/CD](../docs/cicd-vm.md), or [observability](../docs/observability.md). Base development Compose does not include a frontend container; VM Compose does.

Validate the local AI configuration without printing resolved secrets:

```powershell
docker compose --profile ai config --quiet
docker compose --profile ai config --services
```

Then use `docker compose --profile ai up -d --build` and `.\scripts\check-health.ps1 -Profiles ai` from the root. PostgreSQL/Redis use internal networking in the base stack; MinIO ports are published, while Label Studio and MLflow bind to loopback. Use deployment guides for exposure and HTTPS.

`postgres/init-databases.sh` runs only during initial creation of the development database volume. Caddy files configure proxy paths, not application authentication. Monitoring credentials are separate; start from `observability/.env.example` using its guide. Do not print or commit resolved Compose environments.

Named volumes hold database/queue/object/annotation data. `down` retains them; `down -v` destroys them. Host bind-mounted model/data files have a separate lifecycle. Back up both before destructive maintenance.
