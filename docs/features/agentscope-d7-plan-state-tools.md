---
change_ids: ["agentscope-d7-plan-state-tools"]
doc_kind: feature
topics: ["agentscope", "plan_v2", "state-machine", "critical-block"]
created: 2026-03-02
updated: 2026-03-02
status: in_review
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
- 已完成：提交 PR #138，进入评审阶段。
- 待完成：评审反馈处理与合并门禁。

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

### Contract Delta
- `schema`: `Step.status` 与 `PlannerState.plan_status` 引入 `todo/in_progress/done/abandoned` 显式状态语义，`revise_current_plan` 与 `finish_plan` 进入 plan tool 契约。
- `error semantics`: 未新增跨服务 API `error_code` 枚举；本次错误契约沿用框架原生表达（`error_code`/`error_type`/`exception_class`/`ToolResult.error`），并覆盖 pending-step 与非法迁移失败分支。
- `retry`: 重试语义收敛为“仅对非终态 step/plan 允许继续推进”；终态（`done/abandoned`）拒绝回退重试。

### Golden Cases
- 新增/更新 golden 证据文件：`tests/unit/test_plan_v2_tools.py`。
- 契约文档同步：`openspec/changes/agentscope-d7-plan-state-tools/specs/plan-runtime/spec.md`。
- 提示策略同步：`openspec/changes/agentscope-d7-plan-state-tools/specs/chat-runtime/spec.md`。

### Regression Summary
- Runner commands:
  - `pytest -q tests/unit/test_plan_v2_tools.py`
  - `pytest -q tests/unit/test_plan_v2_tools.py tests/unit/test_react_agent_gateway_injection.py tests/unit/test_dare_agent_step_driven_mode.py`
  - `pytest -q`
- Summary: pass 518, fail 0, skip 12.
- Warnings: 1 warning（与 D7 变更无新增失败关联）。

### Observability and Failure Localization
- 生命周期观测链覆盖 `start` / `tool_call` / `end` / `fail` 四类事件。
- 失败定位字段要求保留：`run_id`, `tool_call_id`, `capability_id`, `attempt`, `trace_id`，并至少包含一种错误定位：`error_code`/`error_type`/`exception_class`/`ToolResult.error`。
- 重点定位点：`finish_plan` 失败分支（pending step 保护）、`transition_step/transition_plan` 非法迁移拒绝、sub-agent 调用后状态推进一致性。

### Structured Review Report
- Changed Module Boundaries / Public API: `plan_v2` 新增 `revise_current_plan`、`finish_plan` 两个公开工具，并扩展 `types` 状态机接口。
- New State: 新增 `Step.status` 与 `PlannerState.plan_status` 状态字段；`completed_step_ids` 继续保留为兼容派生状态。
- Concurrency / Timeout / Retry: 未新增并发执行模型；新增工具超时上限分别为 `30s`（revise）与 `20s`（finish）；重试仅允许在非终态路径。
- Side Effects and Idempotency: 主要副作用是 plan 状态推进与 `critical_block` 文本更新；终态回退被拒绝以防重复副作用。
- Coverage and Residual Risk: 覆盖状态迁移、finish/revise、critical_block 分支与回归路径；残余风险在于 legacy step 对象混用场景仍依赖兼容分支。

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
- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/138`
- Implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/138`
- Review 请求：`https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/138#issuecomment-3982413008`
- Merge Gate：待评审通过后补充。
