---
change_ids: ["client-headless-event-envelope-v1"]
doc_kind: feature
topics: ["client-cli", "host-orchestration", "headless-protocol", "issue-135"]
todo_ids: ["CCLI-003", "CCLI-004"]
created: 2026-03-02
updated: 2026-03-02
status: archived
mode: openspec
---

# Feature: client-headless-event-envelope-v1

## Scope

落实 Issue #135 的 Slice B：为 `client/` 增加显式 headless 执行模式，并引入与 legacy automation JSON 分离的 versioned event envelope v1，作为后续外部 control plane 和 capability discovery 的实现前提。

## OpenSpec Artifacts

- Proposal: `openspec/changes/client-headless-event-envelope-v1/proposal.md`
- Design: `openspec/changes/client-headless-event-envelope-v1/design.md`
- Specs:
  - `openspec/changes/client-headless-event-envelope-v1/specs/client-host-orchestration/spec.md`
- Tasks: `openspec/changes/client-headless-event-envelope-v1/tasks.md`

## TODO Coverage

- `CCLI-003`
- `CCLI-004`

## Evidence

### Commands

- `git fetch origin`
- `git worktree add .worktrees/client-headless-event-envelope-v1 -b codex/client-headless-event-envelope-v1 origin/main`
- `./scripts/ci/check_governance_evidence_truth.sh`
- `python3 -m pytest tests/unit/test_client_cli.py -q`
- `openspec --help`
- `openspec change --help`
- `openspec list`
- `openspec show client-headless-event-envelope-v1 --type change --json --no-interactive`
- `openspec validate client-headless-event-envelope-v1 --type change --strict --json --no-interactive`
- `../../.venv/bin/python --version`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'resets_timeout_watch_between_tasks'`
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`
- `./scripts/ci/check_governance_evidence_truth.sh`

### Results

- `git fetch origin`: updated `origin/main` before creating the Slice B worktree.
- `git worktree add .worktrees/client-headless-event-envelope-v1 -b codex/client-headless-event-envelope-v1 origin/main`: created an isolated workspace from merged `main` at commit `793aafa`.
- `./scripts/ci/check_governance_evidence_truth.sh`: passed in the new worktree.
- `python3 -m pytest tests/unit/test_client_cli.py -q`: failed during collection under system Python 3.9 because the code imports `typing.TypeAlias`; this environment cannot yet serve as the verification runtime for Slice B tests.
- `openspec --help` and `openspec change --help`: confirmed the local CLI supports `show` / `validate`, but not scaffold commands such as `new` or `status`, so the Slice B change was created manually.
- `openspec list`: the new change is recognized and now shows `✓ Complete`.
- `openspec show client-headless-event-envelope-v1 --type change --json --no-interactive`: the change exposes 2 `ADDED` deltas under `client-host-orchestration`.
- `openspec validate client-headless-event-envelope-v1 --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).
- `../../.venv/bin/python --version`: confirmed the project virtualenv provides Python `3.14.0`, which is new enough for the current runtime/tests.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'resets_timeout_watch_between_tasks'`: failed before the fix because the second scripted task inherited the first task's approval timeout clock; passed after resetting the approval watch per foreground task.
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`: passed (`40` tests, `0` failures).
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`: passed (`11` tests, `0` failures), including the `script --headless` approval-timeout regression coverage and the scripted timeout-watch reset regression added after PR review.
- `./scripts/ci/check_governance_evidence_truth.sh`: passed after the Slice B evidence block was updated with landed verification commands.

### Behavior Verification

- Happy path: `run --headless` now emits versioned lifecycle frames (`session.started`, `task.started`, `task.completed`) with stable `schema_version/session_id/run_id/seq`, and headless hook events map to structured `tool.invoke` / `tool.result`.
- Error branch: both `run --headless` and `script --headless` approval timeouts now terminate with structured `approval.pending` + `task.failed` frames instead of falling back to inline approval prompts or plain terminal text.

### Risks and Rollback

- Risk: the current headless v1 event surface still lacks external control-plane support, so approval handling remains fail-fast rather than resumable.
- Rollback: revert the Slice B implementation/files and return to the merged Slice A docs baseline where headless remained planned-only.

### Review and Merge Gate Links

- Slice A intent gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/141`
- Slice B implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145`
- Review thread fixed by this follow-up: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145#discussion_r2871270479`
- Related owner comment acknowledged after fix: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145#issuecomment-3983060182`
- Archive target: `openspec/changes/archive/2026-03-02-client-headless-event-envelope-v1/`
