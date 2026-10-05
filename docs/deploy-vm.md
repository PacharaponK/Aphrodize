# Deploy the VM before connecting the GPU worker

Use this standalone Compose file, not the development Compose file or the `ai` profile.
The VM runs PostgreSQL, Redis, MinIO, bucket initialization, API, frontend and Caddy.
Only HTTPS and its HTTP redirect are published, bound to `VM_BIND_IP`.
The GPU worker, trainer, MLflow and Label Studio are not started.

## Settings

Keep `.env` private (mode 600). In addition to existing secrets, set:

```dotenv
VM_HOST=aphrodize.duckdns.org
VM_BIND_IP=172.30.81.237
ANALYSIS_SESSION_SECRET=<unique random secret of at least 32 bytes>
```

These settings have been prepared locally. Confirm the VM still owns that IP.

The DuckDNS A record for `aphrodize.duckdns.org` must point explicitly to
`172.30.81.237`. Do not enable public-IP autodetection for this internal-only
setup. Clients need a network route to the VM (campus network or an authorized
VPN); campus network segmentation may still prevent access. If the campus DNS
blocks public names resolving to private IPs, ask IT for an internal DNS record.
The hostname does not grant network access or enforce campus membership.

After changing `VM_HOST`, rebuild the frontend and recreate only the web services:

```bash
docker compose -f compose.vm.yml build frontend
docker compose -f compose.vm.yml up -d --no-deps --wait frontend caddy
```
Production is explicitly set by this Compose file. Admin functions remain disabled
until separate admin credentials are configured. Secrets are runtime environment
variables, never frontend build arguments or browser variables.

## Validate, audit and start

```bash
cd ~/Aphrodize
docker ps
docker compose -f compose.vm.yml config --quiet
docker compose -f compose.vm.yml build
```

Audit the build image, which includes the pinned package manager. Resolve reachable
high/critical findings before opening the service. The runtime image only needs Next.js.

```bash
docker build --target build -f docker/frontend.Dockerfile -t aphrodize-frontend:build --build-arg SITE_URL=https://aphrodize.duckdns.org .
docker run --rm --entrypoint pnpm aphrodize-frontend:build audit --prod
docker compose -f compose.vm.yml up -d
docker compose -f compose.vm.yml ps
docker compose -f compose.vm.yml exec -T api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8000/api/v1/health').status)"
```

The build runs frontend lint, TypeScript checking and a production build.
If a check or audit fails, fix the issue before starting; do not skip checks.
The VM currently has roughly 4 GiB RAM and no swap; if a build is killed,
build the same image on a machine with more memory and transfer it to the VM.

## Trust HTTPS on Windows

Caddy issues an internal certificate for the configured hostname. Export only the public CA:

```bash
docker compose -f compose.vm.yml cp caddy:/data/caddy/pki/authorities/local/root.crt /home/aphrodize/aphrodize-local-ca.crt
sha256sum /home/aphrodize/aphrodize-local-ca.crt
```

From Windows PowerShell, download it:

```powershell
scp aphrodize@172.30.81.237:~/aphrodize-local-ca.crt "$env:USERPROFILE\Downloads\aphrodize-local-ca.crt"
certutil -hashfile "$env:USERPROFILE\Downloads\aphrodize-local-ca.crt" SHA256
```

Compare the SHA-256 file hashes from both machines; they must match.
Import the public root certificate into the current user's Trusted Root Certification
Authorities using the Windows certificate import wizard. Trust only this VM's CA;
never export or transfer its private key. Then open `https://aphrodize.duckdns.org`.

Verify signup/login, logout, profile and private API behavior from Windows.
Camera capture requires a trusted HTTPS origin.

## Publicly trusted HTTPS on the campus network

The base VM configuration uses Caddy's internal CA. To avoid installing that CA
on each client, use the DuckDNS overlay to obtain a Let's Encrypt certificate
through DNS-01 validation. The VM can remain at its private IP; this does not
make the VM accessible from outside the campus network.

Add `DUCKDNS_API_TOKEN=<your account token>` to the private `.env` (mode 600).
Find the token at the top of your logged-in DuckDNS page. Do not commit it or
paste it into chat. Keep the A record explicitly set to the VM's private IP.
The VM needs outbound HTTPS access to DuckDNS and Let's Encrypt. Both the
DuckDNS module and ACME checks use Docker's resolver (`127.0.0.11:53`), which
forwards to the host's configured DNS. Direct queries to public resolvers may be
blocked on the campus network.

```bash
docker compose -f compose.vm.yml -f compose.duckdns.yml config --quiet
docker compose -f compose.vm.yml -f compose.duckdns.yml build caddy
docker compose -f compose.vm.yml -f compose.duckdns.yml up -d --no-deps caddy
curl --fail https://aphrodize.duckdns.org/login -o /dev/null
```

Use both Compose files for future updates so Caddy keeps the DNS provider and
token needed for automatic renewal. Keep `caddy_data` persistent. Do not use
`down -v`. The base Compose file alone restores the internal-CA configuration.
An issued public certificate publishes the hostname in certificate transparency
logs. The DuckDNS token can modify records for other names in the same account;
use an account dedicated to this site when possible.

## Limits before the GPU is connected

Image inference is unavailable. Do not upload private images in this phase: without
a worker, queued jobs and input deletion will not complete. UV forecasts also require
the excluded model/data/snapshot assets; do not expect them to be populated yet.
The worker connection and a VM-side retention worker remain future work. Database,
Redis and MinIO have no host ports yet; a restricted network path will be added later.

## Updates and data

Review and commit deployment files explicitly; avoid `git add .` for unreviewed data.
Pull approved updates, rebuild, then run `up -d`. Do not use `down -v`: it deletes data.
Keep PostgreSQL, MinIO, `.env` and the Caddy CA volumes backed up securely. A backup
and restore exercise is still required before treating this as a production service.
