# Single-repository CI/CD implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task in the current session. Implementation starts after the owner reviews this revised design and plan.

**Goal:** Publish tested main images and automatically deploy them to the existing VM using a self-hosted runner in PacharaponK/Aphrodize.

**Architecture:** Existing CI stays on GitHub-hosted runners. A release workflow publishes digest-addressed images and a manifest, then deploys through the repository's production environment and self-hosted runner. A VM script preserves production state and restores the previous release on failure.

**Tech stack:** GitHub Actions, GHCR, Docker Buildx, Compose v2, Bash, Python 3, uv, pnpm.

**Spec:** `docs/superpowers/specs/2026-10-06-single-repo-cicd-design.md`

## Global constraints

- One public repository: PacharaponK/Aphrodize. The user accepts repository-level self-hosted runner risk.
- Existing required checks remain Backend CI and Frontend CI on GitHub-hosted runners.
- Publish only a successful main push CI SHA; reject stale candidates before service mutation.
- Build linux/amd64; deploy immutable GHCR digest references.
- Runner labels: self-hosted, linux, x64, aphrodize-deploy; environment: production.
- Default deployment is disabled until owner setup; VM_DEPLOY_ENABLED=true enables automatic deployment.
- Stable .env/assets/volumes remain on the VM; preserve Compose project aphrodize and selected overlays.
- No down, volume deletion, schema rollback, TLS verification bypass or test suppression.
- All images must succeed before publishing a deployable schema-version-1 manifest.

## Review focus

- A successful fork/PR CI run must never schedule publishing or a production runner job.
- A new main commit can supersede an older candidate; reject it before mutation, finish active deployments safely.
- Compose files rendered in release directories must retain the VM's asset/TLS bind paths and active overlays.
- A partial service update or failed rollback must not mark the candidate successful or erase recovery state.
- First deployment must have a verified local baseline, including currently running local image IDs.

## File responsibilities

- `.github/workflows/release.yml`: provenance, hosted build/publish, artifact and self-hosted deploy orchestration.
- `docker/api.Dockerfile`, `pyproject.toml`, `uv.lock`: locked production API dependencies.
- `.dockerignore`: exclude secret/data/generated content from builds.
- `scripts/release_manifest.py`: typed manifest validation and release provenance checks.
- `compose.release.yml`: application image overrides without infrastructure recreation.
- `scripts/deploy-vm.sh`: preflight, lock, pull, update, health, rollback and state transitions.
- `scripts/check-vm-readiness.py`: API container data-service connectivity probe using runtime configuration.
- `tests/test_release_manifest.py`, `tests/test_vm_deployment.py`: provenance and deployment regressions.
- `docs/cicd-vm.md`: repository/runner setup and operator commands.

### Task 1: Locked production image build

**Consumes:** Existing uv.lock, frontend lockfile and production Dockerfiles.
**Produces:** API/frontend/MinIO images buildable for linux/amd64; API imports succeed.

- [x] Add a `production` dependency group containing the existing locked headless OpenCV version, without CI tools; regenerate lock without unrelated upgrades.
- [x] Change API Dockerfile to use locked uv installation in a build stage, exclude GUI OpenCV/dev groups, and copy only the runtime virtualenv/application to the final image.
- [x] Extend .dockerignore for repository logs, datasets and generated outputs; review nested frontend secret exclusion.
- [x] Build API/frontend/MinIO in disposable builds; verify API imports, configured health route and production dependency contents. Run existing CI checks without touching the live stack.
- [x] Commit the isolated build changes.

### Task 2: Release manifest and provenance validation

**Consumes:** Tested SHA, originating CI run metadata, current main SHA and build digest outputs.
**Produces:** JSON schema: `schema_version=1`, `source_sha`, `run_id`, `site_url`, `images={api,frontend,minio}`.

**Interfaces:** `validate_manifest(data: dict) -> dict`, `validate_origin(run: dict, main_sha: str) -> str` in scripts/release_manifest.py; command-line validation accepts JSON files, returns 0 only for valid inputs.

- [x] Write failing tests for a valid main push; reject PR, fork, dev, failed CI and superseded SHA. Validate full 40-hex source SHA, positive run ID, HTTPS origin and exact allowed GHCR digest repositories.
- [x] Run `python -m pytest tests/test_release_manifest.py -q`; verify failures are missing implementation, then implement validation and CLI without executing manifest content as shell code.
- [x] Test missing image, malformed digest, wrong repository, unsupported schema and unsafe SITE_URL inputs. Repeat focused tests and Ruff until passing.
- [x] Commit manifest/provenance implementation and tests.

### Task 3: GitHub-hosted image publishing

**Consumes:** Task 1 Dockerfiles and Task 2 validation contract.
**Produces:** Three GHCR image digests and release-manifest-<SHA> artifact from the current workflow run.

- [x] Add release.yml triggered by completed CI workflow_run. Use event/repository/branch/conclusion guards before scheduling privileged jobs; check out originating head_sha with credentials persistence disabled.
- [x] Validate current main SHA and SITE_URL on a GitHub-hosted job; pin checkout, login, build and artifact Actions by verified full commit SHA.
- [x] Build/push each image with source/revision labels and sha-<SHA> tag. Keep packages:write only on publish jobs; upload the complete manifest after all image builds succeed. Partial publication produces no manifest.
- [x] Validate with actionlint and local provenance tests. Confirm workflow conditions never schedule publish/deploy for PR/dev/fork or failed CI. Document the first-main-run acceptance check.
- [x] Commit workflow publishing changes.

### Task 4: Transactional VM application update

**Consumes:** Validated manifest, VM_DEPLOY_DIR, explicit overlay selection and stable production .env.
**Produces:** Successful current-release.json, retained previous release and recoverable failed candidates.

**Interface:** `bash scripts/deploy-vm.sh --manifest FILE --deploy-dir ABSOLUTE_PATH --overlays CSV`; fake Docker/curl executables on PATH exercise state changes without production containers.

- [x] Write tests that fail until the deployment script exists: missing/unhealthy baseline and pull failures cause no service update; malformed manifests and unsupported overlays are rejected.
- [x] Implement compose.release.yml using API_IMAGE and FRONTEND_IMAGE for api/frontend/minio-init. Render release configuration with preserved production paths and project name; never assume Actions checkout paths are production paths.
- [x] Implement host lock and candidate pulls, bootstrap from running local image IDs, exact bundle capture and service-only update with --no-build. Keep infrastructure outside routine release updates.
- [x] Add readiness probe for PostgreSQL/Redis/MinIO using API runtime settings, container health checks and verified HTTPS login request. Support explicit internal CA trust.
- [x] Test healthy promotion, failure after a partial update, health failure, rollback failure and lock contention. Assert exact previous image restoration, no false successful pointer and no destructive data commands.
- [x] Test overlay selection and asset/TLS bind paths, absent manifests, whitespace in deployment paths and crash-state recovery. Run `python -m pytest tests/test_vm_deployment.py -q`, bash -n and shellcheck.
- [x] Commit deployment script, readiness probe, Compose override and tests.

### Task 5: Self-hosted deploy orchestration and setup guide

**Consumes:** Current-run manifest artifact, production variables and Task 4 CLI.
**Produces:** Automatic deployment on eligible releases only after VM_DEPLOY_ENABLED=true; clear job summary with SHA/digests/outcome.

- [x] Add deploy job to release.yml, dependent on successful publication and enabled deployment. Use exact runner labels, production environment and minimum contents/packages/artifact read permissions.
- [x] Download only the manifest from the same run. Recheck main SHA immediately before VM mutation. Use concurrency without cancel-in-progress; host lock remains the final serialization control.
- [x] Authenticate GHCR using temporary Docker configuration, invoke the reviewed deploy script, clean up credentials on all exits and report rollback separately from successful deployment.
- [x] Write docs/cicd-vm.md with current repo Settings → Actions → Runners registration, runner account/service prerequisites, production environment/main restriction, variables, directory/CA/overlay settings and baseline capture. Registration tokens remain administrator-only and out of chat/source.
- [x] Document manual rollback to the retained bundle, migration limits, failed rollback recovery, first enablement and the later automatic main-release behavior.
- [x] Run actionlint, shell validation and full existing Backend/Frontend CI. Review complete diff for workflow provenance, token scope and production path handling; commit verified changes and push dev for owner merge.

### Task 6: First live publishing and controlled rollout

**Consumes:** Owner-merged main workflow and administrator runner/environment setup.
**Produces:** Evidence of working publication, deployment and recovery; enablement is reported truthfully.

- [ ] Owner sets SITE_URL and VM variables, registers the runner and configures production environment; leave VM_DEPLOY_ENABLED false while validating publishing.
- [ ] After main CI succeeds, verify all images resolve by manifest digest and the artifact points to that same source SHA. Confirm deploy is skipped while disabled.
- [ ] Capture and inspect the first rollback baseline on VM. Present the concrete candidate/baseline to the owner before the first production service update.
- [ ] Enable VM_DEPLOY_ENABLED=true and rerun the eligible release after setup, or merge a new reviewed commit. Confirm stale-release rejection if main has moved.
- [ ] Verify container readiness, HTTPS and signup/login/profile behavior. Run a controlled failed-candidate rollback exercise with owner approval and verify old images are healthy.
- [ ] Record observed workflow links and deployed SHA. Report CD active only after these checks pass; otherwise identify the exact remaining setup or failing check.

## Handoff

This revision replaces the previous private-deploy-repository design. Only design
and plan documentation are changed in this planning turn; no runner, workflow or
production service is modified. Proposed execution is native in this session,
with commits and focused verification per task. The owner reviews the revised
plan before implementation.
