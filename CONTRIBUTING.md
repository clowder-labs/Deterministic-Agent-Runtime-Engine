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

## Run Checks Locally
```bash
python -m pip install -r requirements.txt
ruff check dare_framework tests --select E9,F63,F7
python -m compileall -q dare_framework tests
```

## Team Agent Rules
Read and follow `docs/agent_rules.md` before opening a PR.

## Governance Setup
For GitHub branch protection and merge queue settings, follow `docs/governance/branch-protection.md`.
