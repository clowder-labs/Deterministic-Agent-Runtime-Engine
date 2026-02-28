# 设计可重建性追踪矩阵（Doc -> Code -> Test）

> 更新时间：2026-02-27  
> 目标：为核心能力提供统一可追踪映射，支撑“按文档重建”与漂移校验。

## 使用规则

1. 每条能力必须至少有 1 个设计锚点、1 个实现锚点、1 个测试锚点。
2. `status` 统一使用：`landed` / `partial` / `planned`。
3. 文档与实现变更时必须同步更新本矩阵，否则视为治理未完成。

## 核心能力映射

| Capability | Design Anchor | Code Anchor | Test Anchor | Status |
|---|---|---|---|---|
| Five-layer 编排主循环 | `docs/design/Architecture.md`（3.2） | `dare_framework/agent/dare_agent.py` (`_run_session_loop`/`_run_milestone_loop`) | `tests/unit/test_dare_agent_step_driven_mode.py` | landed |
| Step-driven execute loop | `docs/design/modules/plan/README.md` | `dare_framework/agent/dare_agent.py` (`_run_step_driven_execute_loop`) | `tests/unit/test_dare_agent_step_driven_mode.py` | landed |
| ToolLoop 安全边界（trust/policy/safe execute） | `docs/design/modules/tool/README.md` + `docs/design/modules/security/README.md` | `dare_framework/agent/dare_agent.py` (`_resolve_tool_security`/`_run_tool_loop`) | `tests/unit/test_dare_agent_security_boundary.py` | landed |
| Plan->Execute policy gate | `docs/design/Architecture.md`（4.2/4.3） | `dare_framework/agent/dare_agent.py` (`_check_plan_policy`) | `tests/unit/test_dare_agent_security_boundary.py` | partial |
| EventLog 默认实现（SQLite + hash-chain） | `docs/design/modules/event/README.md` | `dare_framework/event/_internal/sqlite_event_log.py` | `tests/unit/test_event_sqlite_event_log.py` | landed |
| Context 融合组装（STM/LTM/Knowledge + budget degrade） | `docs/design/modules/context/README.md` | `dare_framework/context/context.py` (`DefaultAssembleContext.assemble`) | `tests/unit/test_context_implementation.py` | landed |
| Hook 生命周期接入 | `docs/design/modules/hook/README.md` | `dare_framework/agent/dare_agent.py` (`_emit_hook` 调用链) | `tests/unit/test_dare_agent_security_boundary.py` | partial |
| Documentation-first 治理闭环 | `docs/guides/Documentation_First_Development_SOP.md` | `docs/todos/*` + `openspec/changes/*` | `scripts/ci/check_design_doc_drift.sh` | partial |

## 待收敛关注点（与 status=partial 对应）

1. `Plan->Execute` 的 `APPROVE_REQUIRED` 仍以 fail-fast 为主，需与 ToolLoop 语义统一。
2. Hook payload schema 跨模块 contract 仍在收敛。
3. 文档治理链路已建立，但自动化漂移校验需要持续补强。

## Governance 聚合锚点（新增）

> 说明：治理类 change 需要在本矩阵中补充 `feature aggregation` 锚点，确保从能力声明可直接跳转到变更级证据入口。

| Capability | Feature Aggregation Anchor | OpenSpec Change |
|---|---|---|
| Documentation-first 治理闭环 | `docs/features/enhance-doc-governance-traceability.md` | `openspec/changes/enhance-doc-governance-traceability/` |
