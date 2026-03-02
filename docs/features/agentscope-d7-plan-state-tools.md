---
change_ids: ["agentscope-d7-plan-state-tools"]
doc_kind: feature
topics: ["agentscope", "plan_v2", "state-machine", "critical-block"]
created: 2026-03-02
updated: 2026-03-02
status: draft
mode: openspec
---

# Feature: agentscope-d7-plan-state-tools

## Scope
补齐 AgentScope 迁移 D7：`plan_v2` 计划状态机与原生计划工具能力，覆盖 `todo/in_progress/done/abandoned` 状态语义、`revise_current_plan`、`finish_plan`，并确保 `critical_block` 与真实计划状态同步。

## OpenSpec Artifacts
- Proposal: `openspec/changes/agentscope-d7-plan-state-tools/proposal.md`
- Design: `openspec/changes/agentscope-d7-plan-state-tools/design.md`
- Specs:
  - `openspec/changes/agentscope-d7-plan-state-tools/specs/plan-runtime/spec.md`
  - `openspec/changes/agentscope-d7-plan-state-tools/specs/chat-runtime/spec.md`
- Tasks: `openspec/changes/agentscope-d7-plan-state-tools/tasks.md`

## Progress
- 已完成：D7 kickoff（claim active + docs/design 基线 + OpenSpec 切片初始化）。
- 已完成：D7-1~D7-4 实现（状态机 + revise/finish 工具 + critical_block 联动）。
- 已完成：OpenSpec tasks 全部勾选（12/12）。
- 待完成：提交 PR、评审与合并门禁。

## Evidence

### Commands
- `openspec new change "agentscope-d7-plan-state-tools"`
- `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q`
- `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_plan_v2_tools.py`
- `/Users/lang/workspace/github/Deterministic-Agent-Runtime-Engine/.venv/bin/pytest -q tests/unit/test_plan_v2_tools.py tests/unit/test_react_agent_gateway_injection.py tests/unit/test_dare_agent_step_driven_mode.py`
- `openspec status --change "agentscope-d7-plan-state-tools" --json`

### Results
- 新建 OpenSpec change：`agentscope-d7-plan-state-tools`（schema: `spec-driven`）。
- 当前分支基线：`513 passed, 12 skipped, 1 warning`。
- D7 红灯阶段：`tests/unit/test_plan_v2_tools.py` 初次运行因缺失 `FinishPlanTool` 导致 collection error。
- D7 定向回归：`tests/unit/test_plan_v2_tools.py` => `5 passed`。
- D7 影响面回归：`31 passed, 1 warning`。
- 全量回归：`518 passed, 12 skipped, 1 warning`。
- OpenSpec status：artifacts `proposal/design/specs/tasks` 全部 `done`。

### Behavior Verification
- Happy path：
  - `Planner` 暴露 `revise_current_plan`、`finish_plan` 工具；
  - `revise_current_plan` 可修订计划并按 `step_id` 保留已完成步骤终态；
  - `critical_block` 在步骤全部终态后提示下一步调用 `finish_plan(...)` 收敛计划。
- Error branch：
  - `finish_plan(target_state="done")` 在仍有 pending step 时返回失败；
  - 状态机拒绝终态回退（如 `done -> in_progress`）。

### Risks and Rollback
- 风险：计划状态迁移规则若定义不严谨，可能导致执行循环重复或提前收敛。
- 风险：`critical_block` 与状态不同步会导致提示误导。
- 回滚：保留现有 plan_v2 工具路径与兼容字段（`completed_step_ids`），必要时回退新状态机入口。

### Review and Merge Gate Links
- 待提交 PR 后补充。
