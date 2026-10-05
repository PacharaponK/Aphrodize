# CI and main protection implementation plan

**Goal:** Implement approved CI/CD phases 1–2: validate dev pushes and PRs to main, then require PRs and successful CI for main.

**Architecture:** GitHub-hosted runners execute independent Python and frontend jobs with read-only repository access. Both use committed lockfiles. Production deployment remains a later phase.

**Tech stack:** GitHub Actions, Python 3.11, uv, Node 24, pnpm 11.19.0.

- [x] Add a CI dependency group with headless OpenCV and regenerate uv.lock without upgrading existing packages.
- [x] Add Backend CI and Frontend CI jobs for dev/main pushes, PRs to dev/main, and manual runs; include concurrency and timeouts.
- [x] Verify clean dependency installation, all tests, lint, types and frontend build. Verify a deliberate failure returns nonzero in a disposable checkout.
- [x] Publish dev and inspect successful push/PR checks for commit `140db90`. An existing dev-to-main PR is #12; creating a new PR through the connector returned HTTP 403.
- [ ] Configure main to require PRs, both checks, an up-to-date branch, and resolved conversations; block deletion/force pushes and admin bypass. Preserve existing stronger settings.
- [x] Document exact configuration and any missing administration access.

**Review focus:** Missing dependencies; duplicate check names; skipped workflows caused by path filters; leaked credentials; accidental weakening of existing protection.

## Verification and remaining access

- Clean installs: 294 backend tests, Ruff, 59 frontend tests/fixtures, ESLint, TypeScript and production build passed. Actionlint passed. A disposable assertion-failure probe exited with status 1.
- GitHub push run: https://github.com/PacharaponK/Aphrodize/actions/runs/37290265017 (success for `140db90827217950cdc63d61d71fa60535cdd55a`).
- GitHub PR run: https://github.com/PacharaponK/Aphrodize/actions/runs/37290266898 (success for the same commit). Both required check names were observed with GitHub Actions app ID 15368.
- Main public branch metadata reports protection enabled but no required status-check contexts. The authenticated connector reports repository admin permission, but exposes no branch-protection write tool; its PR-create call returned `403 Resource not accessible by integration`. No authenticated CLI/API credential is available locally. Applying and verifying the live main protection remains pending administrator action. A failing-PR merge-block test requires that live protection first.
