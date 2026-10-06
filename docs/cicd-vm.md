# CI/CD in the existing Aphrodize repository

Everything lives in PacharaponK/Aphrodize. CI and image builds run on GitHub-hosted
runners. Deployment runs on the repository's self-hosted runner on the VM. The
owner explicitly accepted using a public repository with a self-hosted runner.
No second repository or cross-repository token is needed.

## Release flow

Merge dev into protected main → Backend/Frontend CI pass for that commit → Release
workflow builds API, frontend and MinIO → GHCR digest manifest is uploaded →
production runner applies API/frontend → health/readiness/HTTPS checks → success.

Failed CI, PR/dev/fork runs and superseded main candidates cannot enter our
production release path. Publishing all images is required before a manifest is
available. A disabled deploy job does not prevent publishing. MinIO is published
for bootstrap/infrastructure use, but routine application releases never update
PostgreSQL, Redis, MinIO or Caddy.

The manifest records schema_version=1, source_sha, run_id, site_url and images.
Deployment uses image@sha256 references. SHA tags are only for finding images.
Artifacts retain complete manifests for 90 days; the VM retains private current,
previous and historical configuration regardless of artifact expiration.

## Repository configuration (owner)

In Settings → Secrets and variables → Actions → Variables, set:

| Variable | Value |
| --- | --- |
| SITE_URL | `https://aphrodize.duckdns.org` (must match production VM_HOST) |
| VM_DEPLOY_ENABLED | `false` initially; `true` enables automatic production deployment |
| VM_DEPLOY_DIR | Stable absolute production directory, e.g. `/home/aphrodize/Aphrodize` |
| VM_COMPOSE_OVERLAYS | `compose.duckdns.yml` if using DuckDNS; append `,compose.vm-worker-access.yml` only if already active |
| VM_TLS_CA_FILE | Absolute public CA certificate file if using internal Caddy TLS; otherwise unset |

VM_DEPLOY_ENABLED must be a **repository variable** because GitHub checks it before
scheduling the production job. Other VM variables may be repository variables or
production environment variables. Do not place runtime passwords in variables.

Create Settings → Environments → production. Restrict deployment branches to
main. Existing main protection and required CI checks remain in place. Approval
reviewers are optional and would pause automatic deployment until approved.
Review which collaborators can modify workflows and approve fork workflow runs.
Runner labels are routing, not an isolation boundary; the accepted public-runner
risk remains. This workflow's event guards cannot constrain another workflow.

Workflow jobs use GITHUB_TOKEN for GHCR: packages:write only during publishing,
packages:read during deployment. No new PAT is required for packages created by
this repository's workflow. If a pre-existing GHCR package denies access, grant
this repository Actions access in that package's settings. Keep package visibility
private unless the owner deliberately publishes the image contents; a public source
repository does not require public images.

## Runner setup on VM (owner)

The runner is installed on the existing VM so the deploy job can use Docker locally.
Use a dedicated runner account with read access to production configuration and
write access to the production `.releases` directory, not the application's .env
contents in source. Its access to the Docker daemon effectively gives host-level
privileges. Do not mix its workspace with the stable production directory.

Prerequisites: Linux x64, Docker, Compose v2 supporting `--wait` and JSON config,
Bash, Python 3, curl, flock, Git and GitHub runner dependencies. Check:

```bash
docker version
docker compose version
python3 --version
curl --version
command -v flock
```

Docker must work without an interactive sudo prompt **as the runner account**.
Manage its Docker/account permissions explicitly. Do not put `sudo` into workflow
commands as a substitute for provisioning. Runner outbound HTTPS needs GitHub,
Actions artifact services, GHCR and the production hostname. Inbound public SSH
or a public VM address is not required.

Open Settings → Actions → Runners → New self-hosted runner → Linux → x64. Follow
the current download/checksum/install instructions shown by GitHub in a dedicated
directory, such as `/opt/aphrodize-runner`. Register it with:

- Repository URL: https://github.com/PacharaponK/Aphrodize
- Name: aphrodize-vm
- Additional label: aphrodize-deploy
- Work directory: `_work` inside the dedicated runner directory

Use the short-lived registration token only on the VM. Do not paste it into chat,
commit it or save it in `.env`. Install the runner as a service using GitHub's
provided `svc.sh`, configured to run under the dedicated runner account. Keep
runner automatic updates enabled. Confirm it shows Online/Idle in repository
settings before enabling deployment.

## Production directory and first baseline

VM_DEPLOY_DIR points to the directory already used for compose.vm.yml. Keep the
existing `.env` (mode 600), Compose overlays, docker/Caddyfile files and mounted
storage/artifacts/uv in place. Give the runner account only the filesystem access
needed for these existing files and private release state. Do not copy .env into
its Actions checkout or artifacts. Set VM_COMPOSE_OVERLAYS to the actual active
selection, so DuckDNS certificates and worker ports are preserved.

The first deploy captures healthy running api/frontend image IDs and the fully
rendered current Compose configuration before any update. This includes local
`aphrodize-api:vm`/`aphrodize-frontend:vm` images, so initial rollback does not need
old registry tags. A missing/unhealthy service prevents bootstrap.

Rendered configuration contains runtime credentials and is deliberately written
only to VM_DEPLOY_DIR/.releases (mode 700; files mode 600). Never upload or paste
these files into Actions logs, issues or chat. Release-manifest.json contains
image references and source provenance only; it has no production credentials.

Candidate Compose rendering uses the stable production directory explicitly for
all host paths. Persistent volume names and infrastructure configurations must
match the saved current configuration; changes require a separate reviewed
infrastructure operation. Caddy configuration files in the stable directory remain
operator-managed, because routine releases do not recreate Caddy.

Verify the external `/login` URL first. For internal TLS, provide the public CA
certificate via VM_TLS_CA_FILE. Do not disable certificate verification. The deploy
script additionally checks PostgreSQL SELECT 1, Redis PING and both required MinIO
buckets using the API's runtime settings; liveness alone is insufficient.

## First deployment and subsequent automatic releases

1. Merge the reviewed implementation into main, with deployment still disabled.
2. Wait for main CI and all three release image builds. Inspect the Release run's
   `release-manifest-<SHA>` artifact; source SHA and run ID must match that run.
3. Confirm the VM runner is idle, the active overlay selection/origin/CA are correct,
   and existing API/frontend are healthy. Back up production data independently.
4. Review the first candidate before setting VM_DEPLOY_ENABLED=true. This is the
   activation step: future eligible main releases will change production services.
5. Re-run **all jobs** of the eligible Release run on current main, or merge a new
   reviewed commit. If main moved, the old run is rejected as superseded.
6. Confirm the deployment job passes, then test login/logout/profile from an
   authorized client in the VM network. Verify published/deployed source SHA.
7. Exercise a controlled failure and rollback in a disposable stack first. Any
   deliberate production failure test needs explicit approval of the candidate.

Updates pull images first, initialise required buckets, replace only API/frontend
and wait for health. No build occurs on the VM. No `compose down`, volume deletion
or image pruning is part of deployment. Single-VM recreation may briefly interrupt
requests. API startup currently performs schema additions; review migration/backward
compatibility before a release, because image rollback cannot undo schema/data changes.

## Rollback and recovery

Use the checked-out scripts from a reviewed release, with absolute deployment paths.
For manual rollback to the saved previous release:

```bash
bash scripts/deploy-vm.sh --rollback --deploy-dir /home/aphrodize/Aphrodize
```

Add `--ca-file /absolute/path/to/public-root.crt` for internal TLS. Overlays are
already included in stored configuration, so rollback uses the exact saved bundle.
The host lock prevents overlapping deployment or rollback commands.

A failed candidate automatically restores the previous image/configuration and
checks health again. Even when restoration succeeds, the deployment job is red.
The failed candidate remains in private release history and is never promoted.

If the job is killed or restoration fails, pending-release.json is retained and a
new deployment is refused. After inspecting Docker/service health locally, retry
recovery with:

```bash
bash scripts/deploy-vm.sh --recover --deploy-dir /home/aphrodize/Aphrodize
```

Use the same CA option when needed. Retain previous images and release state; do
not run `docker image prune -a`. If previous images are gone, restore them from the
saved registry digest or your independently saved baseline image before recovery.
A recovery failure needs operator intervention; do not delete pending state merely
to make a later job green. Keep database/storage backups separate from image rollback.

## Validation evidence and remaining setup

Local implementation tests use temporary directories and fake Docker/curl commands;
they never update the live VM stack. Production image smoke tests and normal CI
also run in disposable environments. Settings, runner registration and the first
live publication/deployment are administrator actions. A passing dev CI cannot prove
that GHCR publishing or production deployment has already run on main.

References: [workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
[image publishing](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images),
[runner registration](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners).

Implementation verification (2026-10-06): Python 3.11 full suite 350 passed,
frontend 76 passed, ESLint/TypeScript/production build passed, all three production
images built, API smoke imports passed, actionlint and ShellCheck passed. A fresh
review found and fixed rollback history preservation, with a regression test.
Real Compose configuration checks cover base, DuckDNS and worker overlays; a
separate real Docker stack passed readiness and failed correctly with Redis stopped.
Registry publishing and live deployment remain unverified until the owner merges
and completes the setup steps above.
