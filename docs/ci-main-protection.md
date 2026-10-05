# CI and main protection (phases 1–2)

## CI

`.github/workflows/ci.yml` runs on pushes to `dev`/`main`, PRs targeting either
branch, and manual dispatch. No path filters skip required checks. Each job has a
20-minute timeout; newer runs cancel older runs for the same branch or PR.
The workflow uses GitHub-hosted Ubuntu 24.04 runners, read-only repository access,
and commit-pinned Actions. It needs no production secrets or live services.

Required check names must remain exactly (the baseline binds them to the verified
GitHub Actions app ID 15368):

- `Backend CI`: Python 3.11; locked project dependencies plus the `ci` group;
  Ruff and the root pytest suite. Headless OpenCV is included for landmark tests.
- `Frontend CI`: Node 24; pnpm 11.19.0 with the committed pnpm lockfile; ESLint,
  all `tests/*.mjs` (including the cross-layer recommendation fixture), TypeScript
  and the production build.

Reproduce locally from the repository root:

```bash
uv sync --locked --no-default-groups --group ci --no-install-package opencv-python
uv run --no-sync ruff check backend tests
uv run --no-sync python -m pytest
cd frontend
pnpm install --frozen-lockfile --ignore-scripts
pnpm lint
node --test tests/*.mjs
pnpm exec tsc --noEmit
pnpm build
```

This validates web/backend code. GPU/checkpoint integration and production deployment
are separate phases. Root dependencies and CI dependencies are committed in `uv.lock`;
the full GPU runtime requirements are intentionally not installed for these jobs.
`label-studio-sdk` also pulls `opencv-python`. CI omits that GUI distribution and
uses the locked `opencv-python-headless` provider of the same `cv2` module, so two
wheels cannot overwrite each other and tests do not depend on desktop libraries.

## Enable main protection

The committed JSON is a configuration proposal, not proof of live protection.
Run CI once before choosing the required checks. An administrator must apply and
read back the settings in GitHub; committing this file does not apply them.

Open https://github.com/PacharaponK/Aphrodize/settings/branches and add a branch
protection rule matching `main` (or strengthen an existing matching rule):

1. Require a pull request before merging. No mandatory reviewer approval is added
   for the initial setup, so a sole maintainer can use PRs. Preserve any existing
   higher approval requirement.
2. Require status checks to pass: `Backend CI` and `Frontend CI`, selecting the
   GitHub Actions source. Require the branch to be up to date before merging.
3. Require conversation resolution before merging.
4. Do not allow bypassing the above settings, including administrators.
5. Keep force pushes and branch deletion disabled.

If configuring through an authenticated GitHub CLI, inspect current protection first:

```bash
gh api repos/PacharaponK/Aphrodize/branches/main/protection
```

If no rule exists (404), the prepared baseline can be applied from the repo root:

```bash
gh api --method PUT repos/PacharaponK/Aphrodize/branches/main/protection \
  --input .github/main-protection.json
gh api repos/PacharaponK/Aphrodize/branches/main/protection
```

For an existing rule, retain stronger settings, required checks, source bindings and
restrictions; do not blindly overwrite it with the baseline. Existing repository rulesets
can also protect main and must be considered before adding a duplicate rule.

## Acceptance checks

- A dev push and a PR to main produce both checks and pass.
- A deliberate failing test on a disposable PR branch makes its check fail and blocks
  merging. Restore/remove that probe before merging; do not introduce a bypass.
- A PR needs to be current with main and have resolved conversations.
- Verify the protection page/API actually lists the required settings. Only then
  report phase 2 complete.

References: [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/),
[GitHub branch protection API](https://docs.github.com/en/rest/branches/branch-protection).
