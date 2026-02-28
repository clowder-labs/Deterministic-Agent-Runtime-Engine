## Why

`docs/design/Architecture.md` 仍保留若干与当前实现不一致的表述（例如 Hooks 标注为“未接入”、Plan attempt isolation 仍描述为“未实现 snapshot/rollback”）。这会让后续开发和评审基于过时事实决策，违背“文档先行且文档可重建实现”的治理要求。

## What Changes

- 修订 `docs/design/Architecture.md` 中 hooks/sandbox 相关陈旧叙述，使其与 `dare_framework/agent/dare_agent.py`、`dare_framework/hook/*`、`dare_framework/agent/_internal/sandbox.py` 当前实现一致。
- 在同一文档内同步修复与上述事实冲突的相邻状态说明（如控制面“仅接口未接入”的过时描述）。
- 明确本次变更仅做文档事实对齐，不引入运行时行为变更。

## Capabilities

### New Capabilities
- `architecture-documentation-alignment`: 定义架构文档必须反映 hooks 接入与 plan attempt sandbox 基线能力的要求。

### Modified Capabilities
- None.

## Impact

- Affected docs:
  - `docs/design/Architecture.md`
  - `docs/todos/archive/2026-02-27_design_code_gap_todo.md`（回写 DG-001 状态与证据）
- No runtime code path changes.
- No API or dependency changes.
