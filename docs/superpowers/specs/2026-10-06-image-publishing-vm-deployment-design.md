# CI/CD phases 3–4: images and private VM deployment

## Intent and current state

The user approved continuing from successful main CI to image publishing and VM
deployment, and selected a self-hosted runner inside the VM network. Main currently
runs Backend CI and Frontend CI. The VM uses compose.vm.yml, optionally with
compose.duckdns.yml and compose.vm-worker-access.yml. Production configuration and
persistent data already live on the VM. VM address 172.30.81.237 is private.

This is an architectural change: it introduces a registry release interface and
deployment automation across repositories. This document is the proposed design
for review; no runner or production deployment has been installed or performed.

## Approach

Use GitHub-hosted runners in the public application repository for CI and Docker
builds. Publish application images to GHCR only after a successful main push CI
run. Use an independent, private deployment repository with a self-hosted runner
on a dedicated machine inside the VM network. The proposed repository name is
PacharaponK/Aphrodize-deploy; creation needs the owner's GitHub access.

Avoid attaching a persistent production-capable runner to the public application
repository. GitHub warns that public-repository workflows can compromise
self-hosted runners. A separate private deployment repository restricts who can
introduce executable deployment workflows. Its only workflows run protected main
code, never untrusted PR code. The runner host remains separate from production
where practical; its VM access is limited to the deployment account.

Alternative: run the self-hosted runner in the public app repository. This requires
accepting broader workflow access to a persistent machine and is not the selected
design. A VPN from a GitHub-hosted runner would remove persistent runner management,
but the user selected self-hosting and no existing VPN integration was identified.

## Phase 3: release production images

Add a publishing workflow triggered by completed CI runs. Guard it with all of:
original event is push, branch is main, originating repository is this repository,
and conclusion is success. Check out the exact tested SHA. PR and dev runs never
obtain publishing permissions or create deployment releases.

Build API, frontend, and the custom MinIO image for linux/amd64, matching the VM.
The bucket initialization service uses the same API image. Publish each under
ghcr.io/pacharaponk/aphrodize-<service>, tagged sha-<full SHA>, and record immutable
registry digests in a versioned release manifest. A SHA tag is a lookup aid; the
manifest's image@sha256 references are the deploy inputs. Associate images with
the source repository and record the source commit in OCI labels.

API dependencies must use uv.lock rather than the current unconstrained pip
install. Supply the production headless OpenCV runtime without installing the
development or CI tooling in the final image. Verify startup imports and /health
with a disposable API image. Frontend uses its frozen pnpm lockfile and existing
lint, types and production build. SITE_URL is a build argument from a nonsecret
repository variable, validated as the intended HTTPS production origin. Build
caches and context must exclude .env, generated output, datasets and private logs.
No production secrets enter images or workflow artifacts.

Pin third-party Actions by commit. Give publishing jobs contents:read and
packages:write only where needed. A release manifest is made available to the
deployment repository through a release/artifact with source SHA and digest data.
Partial image publication does not produce a deployable manifest. CI or image
build failure cannot trigger deployment.

## Phase 4: deploy on the private network

Provide workflow and bootstrap instructions for the private deployment repo.
The initial workflow uses manual workflow_dispatch with an application commit SHA;
this provides a complete, reviewable deployment path without adding a cross-repo
write token to the public app repository. Require the private repo's protected main
branch and its production environment. Read the exact release manifest from the
application repo and verify its successful publishing run and commit on main.
Never accept arbitrary image registries, shell commands or checkout refs as inputs.

Initial deployment remains manual. Automatic delivery after every main release
can be enabled later through a narrowly scoped cross-repository dispatch credential
after the owner configures the private repo and environment controls. The first
deliverable does not claim automatic production deployment is active.

Use a dedicated self-hosted runner label aphrodize-deploy. CI tests and builds
continue on GitHub-hosted machines. Runner bootstrap requires a short-lived
registration token from the private repo settings; do not store it in source or
paste it into chat. Use a dedicated runner account. Limit repository access,
maintain runner updates, and document the Docker/deployment account privilege.

On the VM, keep a stable deployment directory with .env and persistent assets,
independent of Actions checkouts. A reviewed deploy script receives validated
digest references and a versioned deployment bundle from the tested commit.
Preserve the existing Compose project name aphrodize and volume identities.
Compose overrides select registry images without changing the developer build
flow. Preserve configured DuckDNS and worker-access overlays; never silently
replace Caddy's active TLS configuration.

Serialise production deploys in the workflow and with a host lock. Pull and validate
all images/configuration before changing running services. On first adoption,
capture the currently running image IDs and Compose settings as a rollback
baseline before any update. Update only the application services and the matching
bucket initialization step. Database, Redis, MinIO and Caddy upgrades are explicit
infrastructure operations, outside routine application releases.

Wait for API and frontend container health, then validate the externally served
HTTPS login endpoint with certificate verification. A readiness check should also
confirm the API can reach required data services rather than assuming the current
liveness route proves that. Failure restores the previous deployment bundle and
exact previous API/frontend image references, waits for health again, and reports
both the original failure and rollback result. Rollback success still leaves the
deployment job failed. Persist a successful release pointer only after all checks
pass. Preserve candidate and previous manifests for audit and manual rollback.

Do not use compose down, delete/prune volumes, automatically prune rollback images,
or reset application data. Treat schema/data migrations separately: image rollback
cannot undo a database migration. Validate migrations and backward compatibility
before a release that changes persistent schemas. Document potential short
interruptions during single-VM recreation; this does not promise zero downtime.

## Deliverables

- App repo publishing workflow, locked production API build and release manifest.
- Registry image Compose override with unchanged existing local deployment commands.
- VM deployment script and regression tests using a fake Docker command.
- Private deploy-repo workflow template and runner/environment setup instructions.
- Operator checklist: registry access, origin, VM paths, TLS trust, first baseline,
 manual promotion, health/readiness checks, rollback and recovery.

## Verification and acceptance

Validate workflows with actionlint and shell scripts with shellcheck/bash -n.
Test script transitions: preflight or pull failure does not mutate services;
healthy deploy advances the pointer; health failure restores exact old images;
rollback failure reports failure without overwriting the previous pointer;
overlapping deployments are rejected; malformed digests/paths are rejected;
first deployment requires a captured rollback baseline. Assert no destructive
data commands are issued. Check rendered Compose image references and preserved
project/volume names without printing production environment values.

Run normal Backend CI and Frontend CI. Build candidate images in disposable
containers without touching the live stack. First publishing on main must produce
a complete manifest whose digests resolve. A first production deploy and an
intentional failed-candidate rollback exercise happen only after the owner
configures the private deployment repo, runner and production environment and
approves the candidate release. No production-ready success claim is made until
those live checks have actually completed.

## Operator prerequisites and boundary of automation

The current connector cannot create PRs or administer repository settings and no
authenticated gh CLI token is present. Implementation can produce and push app
repo changes and complete templates, but the owner must create/configure the
private deployment repo, GHCR access, self-hosted registration and environment
rules using their existing administrator access. Never bypass these controls.
The API/image health can be tested in disposable environments; production
service updates wait for the first concrete release and configured deploy path.

## Primary references

- https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners
- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
