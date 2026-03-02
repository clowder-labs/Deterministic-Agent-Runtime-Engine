---
change_ids: ["client-host-orchestration-doc-baseline"]
doc_kind: feature
topics: ["client-cli", "host-orchestration", "headless-protocol", "issue-135"]
todo_ids: ["CCLI-001", "CCLI-002"]
created: 2026-03-02
updated: 2026-03-02
status: active
mode: openspec
---

# Feature: client-host-orchestration-doc-baseline

## Scope

为 Issue #135 建立 docs-only Slice A 基线：纠正 `client/` 作为真实入口的事实，明确宿主编排协议的 planned 边界，并为后续 headless / control plane / capability discovery 实现切片提供统一设计输入。

## OpenSpec Artifacts

- Proposal: `openspec/changes/client-host-orchestration-doc-baseline/proposal.md`
- Design: `openspec/changes/client-host-orchestration-doc-baseline/design.md`
- Specs:
  - `openspec/changes/client-host-orchestration-doc-baseline/specs/client-host-orchestration/spec.md`
- Tasks: `openspec/changes/client-host-orchestration-doc-baseline/tasks.md`

## TODO Coverage

- `CCLI-001`
- `CCLI-002`

## Evidence

### Commands

- `openspec list`
- `openspec --help`
- `openspec change --help`
- `openspec show client-host-orchestration-doc-baseline --type change --json --no-interactive`
- `openspec validate client-host-orchestration-doc-baseline --type change --strict`

### Results

- `openspec list`: confirmed the change must be created manually in the current CLI workflow.
- `openspec --help` and `openspec change --help`: confirmed the local CLI supports `show` / `validate`, but not `new` / `status`.
- `openspec show client-host-orchestration-doc-baseline --type change --json --no-interactive`: confirmed the change exposes 4 `ADDED` deltas under `client-host-orchestration`.
- `openspec validate client-host-orchestration-doc-baseline --type change --strict`: passed (`1/1` change valid, `0` issues).

### Behavior Verification

- Happy path: Slice A now records the host orchestration baseline in `client/DESIGN.md`, clarifies the current `--output json` boundary in `client/README.md`, and binds the same scope to TODO + OpenSpec + feature evidence.
- Error branch: the docs now explicitly record that current automation JSON is not the future host protocol, preventing later slices from treating the existing `log/event/result` schema as a stable host contract.

### Risks and Rollback

- Risk: the design baseline may drift from future implementation slices if Slice B/C/D do not consume the same capability spec.
- Rollback: revert this docs-only slice and keep `client` documented only as the current automation CLI without host-orchestration commitments.

### Review and Merge Gate Links

- Pending in current branch（待创建 docs-only intent PR 后补充）。
