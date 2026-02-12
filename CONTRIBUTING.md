# Contributing Guide

This repository uses PR-based delivery with CI gates to keep `main` stable under parallel agent development.

## Branching and Merge Policy
- Do not push directly to `main`.
- Use feature branches and open a PR.
- Keep each PR focused on one objective.
- Fill every section of `.github/pull_request_template.md`.

## Required CI Checks (phase-1)
- `lint` (Ruff syntax/parser safety set)
- `build` (Python compile check)

These checks are designed to be fast and low-friction first. We will tighten them in later phases.

## Smoke Tests (phase-2 rollout)
- CI job: `smoke-tests`
- Current mode: non-blocking (`continue-on-error`), used as signal collection before becoming required.
- Scope: `tests/smoke/` only, deterministic checks with no external model calls.

## Risk Matrix (phase-3)
- CI job: `risk-matrix`
- Current scope:
  - `tests/unit/test_a2a.py` (auth gate path)
  - `tests/unit/test_transport_channel.py` (concurrency/backpressure path)
  - `tests/unit/test_execution_control.py` (execution control and risk path)

## Skip/Only Guard
- CI job: `test-skip-guard`
- Any newly added `skip/skipif/xfail/only` marker in changed Python lines fails this check.
- If a temporary skip is unavoidable, document why in PR risk section and get explicit review.

## Lockfile Policy
- CI job: `lockfile-policy`
- If lockfiles change (`poetry.lock`, `Pipfile.lock`, `uv.lock`, `requirements.lock`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`), the dependency manifest must also change in the same PR (`requirements.txt`, `pyproject.toml`, or `package.json`).

## Run Checks Locally
```bash
python -m pip install -r requirements.txt
ruff check dare_framework tests --select E9,F63,F7
python -m compileall -q dare_framework tests
pytest -q tests/smoke -m smoke
./scripts/ci/run_risk_matrix.sh
./scripts/ci/check_test_skip_markers.sh
./scripts/ci/check_lockfile_policy.sh
```

## Team Agent Rules
Read and follow `docs/agent_rules.md` before opening a PR.
Team collaboration playbook: `docs/guides/Team_Agent_Collab_Playbook.md`.

## Governance Setup
For GitHub branch protection and merge queue settings, follow `docs/governance/branch-protection.md`.

## Free-Tier Main Guard (Direct Push Fallback)
- Workflow: `.github/workflows/main-guard.yml`
- Trigger: every `push` to `main`
- Behavior:
  - Detect commits on `main` without PR association metadata
  - Open an incident issue automatically
  - In `revert-pr` mode, open an automatic rollback PR for unlinked commits
  - Mark the run as failed for clear red-signal audit trail

### Repository Variables
- `MAIN_GUARD_MODE`: `revert-pr` (default) or `alert-only`
- `MAIN_GUARD_ALLOW_ACTORS`: comma-separated actor allowlist for emergency/bot bypass
- `MAIN_GUARD_ALLOW_MARKER`: commit marker to bypass incident (default `[main-guard:allow-direct-push]`)

Use bypass only for emergency hotfixes and always attach a postmortem note in follow-up PR/issue.

## Manual Merge Guard (No Auto-Self-Merge Fallback)
- Workflow: `.github/workflows/manual-merge-guard.yml`
- Trigger: every merged PR close event on `main` (`pull_request_target: closed`)
- Policy:
  - merged PR must have at least one independent `APPROVED` review
  - self-merge (`author == merged_by`) is treated as non-compliant by default
  - non-compliant merge triggers incident issue + optional rollback PR

### Repository Variables
- `MANUAL_MERGE_GUARD_MODE`: `revert-pr` (default) or `alert-only`
- `MANUAL_MERGE_GUARD_ALLOW_MERGERS`: comma-separated emergency allowlist for mergers

This is a free-tier fallback when GitHub branch protection/rulesets are not available on private repositories.
