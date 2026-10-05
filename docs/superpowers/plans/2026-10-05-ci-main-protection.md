# CI and main protection implementation plan

**Goal:** Implement approved CI/CD phases 1–2: validate dev pushes and PRs to main, then require PRs and successful CI for main.

**Architecture:** GitHub-hosted runners execute independent Python and frontend jobs with read-only repository access. Both use committed lockfiles. Production deployment remains a later phase.

**Tech stack:** GitHub Actions, Python 3.11, uv, Node 24, pnpm 11.19.0.

- [ ] Add a CI dependency group with headless OpenCV and regenerate uv.lock without upgrading existing packages.
- [ ] Add Backend CI and Frontend CI jobs for dev/main pushes, PRs to dev/main, and manual runs; include concurrency and timeouts.
- [ ] Verify clean dependency installation, all tests, lint, types and frontend build. Verify a deliberate failure returns nonzero in a disposable checkout.
- [ ] Publish dev, open a PR to main, and inspect GitHub checks.
- [ ] Configure main to require PRs, both checks, an up-to-date branch, and resolved conversations; block deletion/force pushes and admin bypass. Preserve existing stronger settings.
- [ ] Document exact configuration and any missing administration access.

**Review focus:** Missing dependencies; duplicate check names; skipped workflows caused by path filters; leaked credentials; accidental weakening of existing protection.
