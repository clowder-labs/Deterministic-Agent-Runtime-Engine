# Main Branch Protection and Merge Queue Setup

This checklist is the source of truth for enabling merge gates on `main`.

## Required GitHub Settings for `main`
In **Settings -> Branches -> Add rule** (branch name pattern: `main`):

1. Enable `Require a pull request before merging`.
2. Set required approvals to at least `1`.
3. Enable `Dismiss stale pull request approvals when new commits are pushed`.
4. Enable `Require review from Code Owners`.
5. Enable `Require conversation resolution before merging`.
6. Enable `Require status checks to pass before merging` and add:
   - `lint`
   - `build`
7. Enable `Require branches to be up to date before merging`.
8. Disable direct pushes (do not grant bypass except emergency admins).
9. Disable force pushes.
10. Disable branch deletion.

## Merge Queue (Preferred)
If your GitHub plan supports merge queue:

1. Enable `Require merge queue` for `main`.
2. Keep required checks as `lint` and `build` initially.
3. Start with a conservative queue strategy (small batches, low parallelism).
4. Add `merge_group` workflow trigger support (already included in `.github/workflows/ci-gate.yml`).

## Phase Rollout for Required Checks
- Phase 1 (now, required): `lint`, `build`
- Phase 2 (observe first, then required): `smoke-tests`
- Phase 3 (after 1-2 stable weeks, then required): `risk-matrix`, `test-skip-guard`, `lockfile-policy`

## Fallback if Merge Queue Is Unavailable
Use pre-merge combined checks:

1. Keep `Require branches to be up to date before merging` enabled.
2. Keep PR checks running on GitHub's synthetic merge commit (default `pull_request` behavior).
3. Require a fresh green run after rebasing/cherry-picking onto latest `main`.

## Free-Tier Fallback if Branch Protection Is Unavailable
Use `.github/workflows/main-guard.yml` as an automated guard rail:

1. Detect pushes to `main` where commits have no associated PR metadata.
2. Open an incident issue automatically with run link and commit context.
3. In `MAIN_GUARD_MODE=revert-pr`, auto-create a rollback PR that reverts unlinked commits.
4. Fail the `main-guard` run intentionally so incidents are visible in Actions history.

### Variables (Repository -> Settings -> Secrets and variables -> Actions -> Variables)
- `MAIN_GUARD_MODE`
  - `revert-pr`: detect + issue + rollback PR (recommended default)
  - `alert-only`: detect + issue only
- `MAIN_GUARD_ALLOW_ACTORS`
  - Comma-separated pusher names allowed to bypass detection (emergency admins/bots)
- `MAIN_GUARD_ALLOW_MARKER`
  - Commit message override marker (default `[main-guard:allow-direct-push]`)

This fallback does not replace native branch protection, but it gives enforceable detection and remediation when plan limits block branch rules.

## Verification Steps
1. Open a small PR.
2. Confirm `lint` and `build` run automatically.
3. Confirm merge is blocked while checks are failing.
4. Confirm merge is allowed only after all required checks are green.
