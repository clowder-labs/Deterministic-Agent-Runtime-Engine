---
change_ids: ["client-capability-discovery-and-host-tests"]
doc_kind: feature
topics: ["client-cli", "host-orchestration", "capability-discovery", "issue-135"]
todo_ids: ["CCLI-007", "CCLI-008"]
created: 2026-03-02
updated: 2026-03-02
status: active
mode: openspec
---

# Feature: client-capability-discovery-and-host-tests

## Scope

落实 Issue #135 的 Slice D：为 `client/` 的宿主协议面补上显式 capability discovery（`actions:list`），并建立覆盖 headless event envelope、control plane 与 discovery 的宿主级回归测试。

## OpenSpec Artifacts

- Proposal: `openspec/changes/client-capability-discovery-and-host-tests/proposal.md`
- Design: `openspec/changes/client-capability-discovery-and-host-tests/design.md`
- Specs:
  - `openspec/changes/client-capability-discovery-and-host-tests/specs/client-host-orchestration/spec.md`
- Tasks: `openspec/changes/client-capability-discovery-and-host-tests/tasks.md`

## TODO Coverage

- `CCLI-007`
- `CCLI-008`

## Evidence

### Commands

- `git fetch origin`
- `git worktree add .worktrees/client-capability-discovery-and-host-tests -b codex/client-capability-discovery-and-host-tests origin/main`
- `openspec archive client-external-control-plane-v1 -y`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'bridges_additional_host_actions'`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'actions_list or startup_handshake or bridges_additional_host_actions or control_stdin_bridges_actions_list'`
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`
- `openspec list`
- `openspec show client-capability-discovery-and-host-tests --type change --json --no-interactive`
- `openspec validate client-capability-discovery-and-host-tests --type change --strict --json --no-interactive`
- `./scripts/ci/check_governance_evidence_truth.sh`

### Results

- `git fetch origin`: confirmed `origin/main` has merged Slice C via PR `#151`.
- `git worktree add .worktrees/client-capability-discovery-and-host-tests -b codex/client-capability-discovery-and-host-tests origin/main`: created an isolated Slice D workspace from merged `main` at commit `cce6e4d`.
- `openspec archive client-external-control-plane-v1 -y`: archived the completed Slice C change to `openspec/changes/archive/2026-03-02-client-external-control-plane-v1/` and synced the landed control-plane deltas back into the main `client-host-orchestration` spec.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'bridges_additional_host_actions'`: failed before the implementation because `actions:list` returned `ok=false` as an unsupported control action; passed after exposing explicit discovery on the CLI host bridge.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q -k 'actions_list or startup_handshake or bridges_additional_host_actions or control_stdin_bridges_actions_list'`: passed (`8` tests), covering run/script discovery, coexistence with approvals, and the absence of unsolicited startup handshake frames.
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`: passed (`45` tests, `0` failures) after the Slice D discovery bridge landed.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`: passed (`25` tests, `0` failures) after the Slice D capability-discovery regressions were added.
- `openspec list`: shows the change as `client-capability-discovery-and-host-tests     ✓ Complete` after implementation, docs, and evidence tasks were synchronized.
- `openspec show client-capability-discovery-and-host-tests --type change --json --no-interactive`: confirms the change exposes `1` `MODIFIED` delta under `client-host-orchestration`.
- `openspec validate client-capability-discovery-and-host-tests --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).
- `./scripts/ci/check_governance_evidence_truth.sh`: passed after the Slice D implementation evidence was synchronized with the updated tasks and README / DESIGN claims.

### Behavior Verification

- Happy path: `run/script --headless --control-stdin` now exposes explicit `actions:list`, and the discovery result returns the current CLI host protocol surface without delegating to the runtime action dispatcher.
- Happy path: `actions:list` coexists with existing approvals / MCP / skills / status control actions in the same headless session, preserving request correlation and structured responses.
- Error branch: headless sessions still do not emit unsolicited startup handshake frames; hosts must request discovery explicitly, which keeps the stdout protocol free of implicit capability chatter.

### Risks and Rollback

- Risk: the explicit discovery list is intentionally narrow and returns only canonical action ids, so hosts that want richer metadata still need a later protocol slice.
- Rollback: revert the Slice D implementation/files and return to the archived Slice C baseline where control is available but explicit `actions:list` discovery is not.

### Review and Merge Gate Links

- Slice C implementation gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/151`
- Slice C archive target: `openspec/changes/archive/2026-03-02-client-external-control-plane-v1/`
- Slice D intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/156`
