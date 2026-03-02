## Why

Issue #135 暴露的核心问题不是 `client/` 缺少基础 CLI 能力，而是仓库缺少一份关于“宿主如何稳定托管 `client/`”的 canonical 设计基线。  
当前代码已经具备 `run/script`、`--output json`、`skills list`、`mcp reload/unload` 等能力，但它们仍停留在“可脚本化 / 可调试”的层级，尚未被定义为显式的 host orchestration contract。

如果直接进入实现 Slice B/C/D，会产生三个风险：

1. 把现有 `--output json` 误当作长期宿主协议，造成兼容风险。
2. 在没有 headless/control plane 明确边界时，把 prompt / inline approval / transport action 混杂到同一层。
3. 后续实现缺少可追踪的 docs baseline，无法满足仓库 docs-first SOP。

因此需要先做一个 docs-only Slice A，建立后续实现的唯一设计输入。

## What Changes

- 更新 `client/DESIGN.md`，明确 interactive / automation-json / headless 三层模式边界。
- 更新 `client/README.md`，澄清当前 `--output json` 的 legacy automation 属性与兼容边界。
- 同步 `docs/design/modules/event/README.md` 与 `docs/design/TODO_INDEX.md`，把 host-orchestrated client envelope 纳入 canonical design backlog。
- 新增 OpenSpec capability `client-host-orchestration`，记录后续 headless event envelope、structured control plane、capability discovery 的目标约束。
- 创建 feature aggregation 文档，作为当前 Slice A 的状态与证据源。

## Capabilities

### New Capabilities

- `client-host-orchestration`: 定义 `client/` 作为外部宿主可编排 CLI 时的模式边界、事件协议、控制面与能力发现约束。

### Modified Capabilities

- `interaction-dispatch`: 补充宿主能力发现与结构化 control plane 的规划约束。
- `transport-channel`: 补充宿主事件 envelope 的版本化与关联字段要求。

## Impact

- 影响文件：
  - `client/DESIGN.md`
  - `client/README.md`
  - `docs/design/modules/event/README.md`
  - `docs/design/TODO_INDEX.md`
  - `docs/todos/2026-03-02_client_cli_host_orchestration_master_todo.md`
  - `docs/features/client-host-orchestration-doc-baseline.md`
  - `openspec/changes/client-host-orchestration-doc-baseline/**`
- 代码影响：无，本 change 仅建立 docs baseline 与后续实现约束。
- 流程影响：后续 Slice B/C/D 必须消费本 change 的 TODO 子集与 capability 要求，不允许绕过 docs-only intent PR 直接实现。
