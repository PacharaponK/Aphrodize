# Single-repository CI/CD design (phases 3–4)

## Agreed intent

Keep CI, image publishing, deployment scripts and the self-hosted runner in the
existing public repository PacharaponK/Aphrodize. The user explicitly accepts the
risk of a self-hosted runner attached to a public repository and rejects the
previous proposal to create a private deployment repository. No second repository,
VPN or pull agent is part of this design.

Main already has Backend CI and Frontend CI. The VM is on the private network at
172.30.81.237. It uses compose.vm.yml, optionally compose.duckdns.yml and
compose.vm-worker-access.yml. Its .env, model assets and data volumes stay on the VM.
This document proposes the remaining work; no runner or deployment is active yet.

## Flow

1. Push dev or open a PR: existing CI runs on GitHub-hosted runners.
2. Merge main: existing CI runs again for the merge commit.
3. Successful main push CI: release.yml checks provenance and builds production
   images on GitHub-hosted Ubuntu 24.04, publishing them to GHCR.
4. Once the complete manifest exists, a deployment job in that same workflow runs
   on [self-hosted, linux, x64, aphrodize-deploy], using environment production.
5. The runner applies the images on the VM and checks readiness and HTTPS. Failure
   triggers restoration of the previous release and fails the deployment job.

Use workflow_run for completed CI. Require the original event to be push, branch
main, repository PacharaponK/Aphrodize and conclusion success. Resolve the exact
workflow_run.head_sha, never assume github.sha identifies the tested commit.
Reject commits superseded by a newer main head before publication and immediately
before changing VM services. A newer push after deployment starts is handled by
finishing the current deployment safely, then deploying the next candidate.
PR, fork, dev and failed CI events must not schedule this production runner job.
These checks constrain our workflow; labels and environment rules do not sandbox
other workflows that might target a repository-level runner. This residual risk
is accepted by the user, not claimed to be eliminated.

## Phase 3: image publishing

Build linux/amd64 API, frontend and custom MinIO images. The bucket-init service
uses the API image. Publish under ghcr.io/pacharaponk/aphrodize-<service> with
sha-<full commit SHA> tags and OCI source/revision labels. Deploy by immutable
image@sha256 digest, not a mutable tag. MinIO is published for infrastructure
bootstrap; routine app deploys do not recreate MinIO, Redis, PostgreSQL or Caddy.

A schema-version-1 JSON manifest contains source_sha, run_id, site_url and images
(api, frontend, minio). Each image value is a fully qualified digest reference.
Upload it as release-manifest-<SHA> after all builds succeed. Deploy consumes only
that artifact from its own workflow run. Manual rollback uses retained local
manifests; it does not rebuild or accept arbitrary images.

Use uv.lock for API dependencies and a production group for headless OpenCV;
exclude GUI OpenCV and dev/CI groups. The final image does not contain uv or test
tools. Frontend retains frozen pnpm dependencies and build checks. Set SITE_URL
from the nonsecret repository variable SITE_URL; require an HTTPS origin without
credentials, path, query or fragment. Exclude .env, logs, datasets, storage and
build output from the image context. Keep runtime credentials on the VM.

Pin Actions by commit. Default workflow permissions are contents:read; grant
packages:write to publish jobs and packages:read to deploy only. Use temporary
Docker credentials and clean up authentication even on failure. Release jobs run
with cancellation disabled so deployment cannot be interrupted by concurrency.

## Phase 4: VM deployment

Register a repository-level runner with label aphrodize-deploy on the VM, under a
dedicated account, using a short-lived token from this repository's settings.
Registration remains an administrator setup action; no token is committed.
Use environment production restricted to main. Do not require a second maintainer
for routine deploys; optional approval gates can be added later. Keep existing
main protection and control who can edit workflows and approve fork workflows.

The runner needs Docker, Compose v2, Python 3, curl, flock, outbound HTTPS to GitHub
and GHCR, and access to the deployment directory. Docker access is a privileged
capability. The runner workspace is separate from the stable production directory.
Provide instructions to keep the runner updated and run it as a service.

Configure nonsecret variables SITE_URL, VM_DEPLOY_DIR (absolute directory),
VM_COMPOSE_OVERLAYS (comma-separated approved basenames; empty means base-only),
and VM_DEPLOY_ENABLED. Enable only after bootstrap verification; unset/false skips
the deploy job while still allowing image publishing. Once enabled, each eligible
main release deploys automatically; there is no manual dispatch requirement.

Provide compose.release.yml to override only api, frontend and minio-init images.
Use the stable production .env explicitly and preserve Compose project aphrodize,
volume names, mounted UV assets and the selected DuckDNS/worker overlays. Copy only
versioned deployment files into a release directory, never overwrite .env or use
an Actions checkout as a production bind-mount root. Preserve absolute host paths
for assets and TLS config when rendering the release configuration.

Acquire a host lock and validate the manifest, image allowlist/digests, configuration
and baseline. Pull candidate images before mutation. First adoption captures the
running API/frontend image IDs and current Compose bundle; reject bootstrap if
these services or required baseline configuration are missing or unhealthy.
Update application services and bucket-init with --no-build; do not run down or
recreate unrelated services. Record service changes before health polling so the
failure path can roll back partial updates. Wait for container health, validate
API connectivity to PostgreSQL, Redis and MinIO, and verify the HTTPS /login route.
Use the configured CA for internal TLS; never use curl -k.

On failure, restore the previous bundle and exact image references, then check
health again. A successful rollback still returns a failed deployment result.
An unsuccessful rollback reports both failures and retains recovery information.
Advance current-release.json atomically only after success, and retain
previous-release.json plus candidate history. Image rollback cannot reverse schema
changes: review backward-compatible migrations separately. Single-VM restarts may
cause a short interruption; zero downtime is not promised.

## Acceptance and setup boundary

Test manifest validation, source provenance, stale release rejection, preflight
and pull failures, successful promotion, partial update/health failures, rollback
failure, lock contention, baseline capture and overlay/path preservation. Assert
no destructive data operations. Validate workflows and shell syntax, run both
existing CI suites and build/smoke-test images in disposable containers.

Owner configuration is needed for runner registration, production environment,
variables and GHCR access. The current connector cannot administer these settings.
After the workflow reaches main, verify a complete published manifest, perform the
first concrete deployment, and exercise a controlled rollback before claiming
live CD works. Until VM_DEPLOY_ENABLED is true and those checks pass, report image
publishing and deploy preparation separately from operational deployment.

## References

- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run
- https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
