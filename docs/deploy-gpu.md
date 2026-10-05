# Windows GPU worker using an SSH tunnel

The Windows GPU test passed on a GTX 1660 SUPER, 6 GiB VRAM, using PyTorch 2.1.2.
This configuration retains PyTorch 2.1.2 / CUDA 11.8 and uses Python 3.11, required
by the worker's `datetime.UTC` imports. The downloaded PyTorch image remains a
successful hardware probe; the worker image includes the project's dependencies.
This setup has not yet been built or run with the owner's checkpoints.

## VM prerequisites

First build and validate the VM services following `docs/deploy-vm.md`. For worker
access, always include both VM files in subsequent Compose commands:

```bash
cd ~/Aphrodize
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml config --quiet
docker compose -f compose.vm.yml -f compose.vm-worker-access.yml up -d
```

PostgreSQL, Redis and MinIO ports bind only to VM loopback, not the LAN. A trusted
SSH connection carries worker traffic. Keep the GPU worker off while VM startup,
frontend checks, dependency audits and database/storage initialization are incomplete.
The worker gets matching database/Redis/MinIO credentials, not the API or JWT secret.
These prototype service credentials still allow broad data access; use only a trusted
worker machine. Dedicated restricted roles are future hardening work.

## Transfer the prepared setup

From Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force C:\Users\student\ai-eco\aphrodize-gpu-runtime
cd C:\Users\student\ai-eco\aphrodize-gpu-runtime
scp aphrodize@172.30.81.237:~/aphrodize-gpu-setup.tar.gz .
tar -xzf .\aphrodize-gpu-setup.tar.gz
scp aphrodize@172.30.81.237:~/Aphrodize/.env.gpu .
```

This separate runtime folder avoids overwriting the existing Windows project. Source
files come from the same VM snapshot. Models stay in the original project directory.
Treat `.env.gpu` as a secret: never print, paste, commit or share it. Restrict local
access to your Windows user. The source archive contains no credentials or models.

## Keep the SSH tunnel running

Open a separate PowerShell window:

```powershell
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:15432:127.0.0.1:5432 -L 127.0.0.1:16379:127.0.0.1:6379 -L 127.0.0.1:19000:127.0.0.1:9000 aphrodize@172.30.81.237
```

Authenticate interactively. Keep the window open; Ctrl+C closes the tunnel.
No output after authentication is normal. Container access uses `host.docker.internal`.
Verify that it reaches the Windows loopback forwarders before starting the worker.
Do not change bindings to `0.0.0.0` if the probe fails; diagnose Docker Desktop routing.

## Build the worker, then probe container connectivity

In the runtime folder:

```powershell
docker compose --env-file .env.gpu -f compose.gpu.yml config --quiet
docker compose --env-file .env.gpu -f compose.gpu.yml build
docker compose --env-file .env.gpu -f compose.gpu.yml run --rm --no-deps --entrypoint python inference-worker -c "import socket; [socket.create_connection(('host.docker.internal',p),5).close() for p in (15432,16379,19000)]; print('TCP connectivity OK')"
```

This only verifies TCP access. Verify credentials and a dummy object round trip next.
The diagnostic creates no inference jobs and uses no private images:

```powershell
$probe = @'
import asyncio
from uuid import uuid4
from sqlalchemy import text
from backend.core.db.session import SessionLocal, close_database
from backend.libs.redis_client import get_arq_pool
from backend.libs.minio_client import put_bytes, get_bytes, remove_objects

async def main():
    stage = "Redis"
    try:
        redis = await get_arq_pool()
        try:
            assert await redis.ping()
            print("Redis authentication: OK")
        finally:
            await redis.aclose()
        stage = "PostgreSQL"
        try:
            async with SessionLocal() as session:
                assert await session.scalar(text("SELECT 1")) == 1
            print("PostgreSQL authentication: OK")
        finally:
            await close_database()
        stage = "MinIO"
        key = "diagnostics/" + str(uuid4()) + ".txt"
        payload = b"aphrodize-connectivity-test"
        try:
            await asyncio.to_thread(put_bytes, key, payload, "text/plain")
            assert await asyncio.to_thread(get_bytes, key) == payload
        finally:
            await asyncio.to_thread(remove_objects, [key])
        print("MinIO write/read/delete: OK")
    except Exception as error:
        print(stage + " probe failed: " + type(error).__name__)
        raise SystemExit(1) from None

asyncio.run(main())
'@
$probe | docker compose --env-file .env.gpu -f compose.gpu.yml run --rm -T --no-deps --entrypoint python inference-worker -
```

Do not print raw exception messages or credentials. Resolve a failed probe before
starting real jobs. The diagnostic object should be removed even if the read fails.

## Verify the default model mount and CUDA

```powershell
docker compose --env-file .env.gpu -f compose.gpu.yml run --rm --no-deps --entrypoint python inference-worker -c "import torch; from ai.ffhq_wrinkle.modeling import load_wrinkle_model; assert torch.cuda.is_available(); torch.cuda.reset_peak_memory_stats(); b=load_wrinkle_model('UNet',requested_device='cuda'); torch.cuda.synchronize(); print('Model device:',b.device); print('Checkpoint SHA256:',b.checkpoint_sha256); print('Load peak allocated MiB:',torch.cuda.max_memory_allocated()/1024**2)"
```

The loader checks checkpoint SHA-256 and architecture before loading. The official
UNet checkpoint expected hash is
`883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25`.
Loading-memory results do not measure full pipeline peak memory. A real consented
image test must cover preprocessing, face parsing, MediaPipe, inference, persisted
results and deletion before calling the GPU deployment ready. The archive ZIP and
SwinUNETR checkpoint are not selected by this default UNet worker.

## Start only after the probes pass

```powershell
docker compose --env-file .env.gpu -f compose.gpu.yml up -d --no-deps inference-worker
docker compose --env-file .env.gpu -f compose.gpu.yml logs --tail 50 inference-worker
```

Worker concurrency remains one job. Verify queued -> running -> completed from the
web, GPU activity and the original-image deletion. Review quality rejection and
worker-disconnection behavior too. Do not assume a restart recovers every running
job: recovery/retention behavior must be tested separately. The worker still owns
24-hour result cleanup; keep it and the tunnel running. A VM-side retention worker
is outstanding before unattended production use.
