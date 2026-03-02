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
- `../../.venv/bin/python -m pytest tests/unit/test_client_cli.py -q`: passed (`45` tests, `0` failures) as the Slice D kickoff baseline in the new worktree.
- `../../.venv/bin/python -m pytest tests/integration/test_client_cli_flow.py -q`: passed (`21` tests, `0` failures) as the Slice D kickoff baseline in the new worktree.
- `openspec list`: shows the new change as `client-capability-discovery-and-host-tests     0/7 tasks`.
- `openspec show client-capability-discovery-and-host-tests --type change --json --no-interactive`: confirms the change exposes `1` `MODIFIED` delta under `client-host-orchestration`.
- `openspec validate client-capability-discovery-and-host-tests --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).
- `./scripts/ci/check_governance_evidence_truth.sh`: passed after the Slice C archive moves and Slice D kickoff evidence were synchronized.

### Behavior Verification

- Happy path: Slice C is now archived on top of merged `main`, and Slice D design chooses explicit `actions:list` discovery on `--control-stdin` rather than adding startup chatter to the host protocol.
- Error branch: unsolicited startup capability handshake remains out of scope for v1, preventing hosts from depending on implicit frames before explicit discovery semantics are finalized.

### Risks and Rollback

- Risk: until Slice D implementation lands, hosts still need a hardcoded discovery matrix even though the design baseline now prefers explicit `actions:list`.
- Rollback: drop the Slice D kickoff change and keep the repository at the archived Slice C baseline where control is available but capability discovery remains planned-only.

### Review and Merge Gate Links

- Slice C implementation gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/151`
- Slice C archive target: `openspec/changes/archive/2026-03-02-client-external-control-plane-v1/`
- Slice D intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/156`
