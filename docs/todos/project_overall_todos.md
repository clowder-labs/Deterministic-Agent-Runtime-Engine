# DARE Framework 项目总体 TODO

> 更新时间：2026-03-04  
> 范围：项目全局演进（非单个 feature 的实现方案）

## 1. 目标与边界

- 目标：持续收敛 `docs/design` 目标架构与 `dare_framework/` 当前实现，优先保证可运行、可验证、可审计。
- 边界：这里只记录跨模块、跨阶段事项；具体任务拆解进入 OpenSpec 与模块文档。
- 当前并行约束：最多 3 人并行开发（同一时刻最多 3 个 `active` claim），但任务拆分主轴以“依赖关系 + 重要程度 + 复杂度”为准。

## 1.1 认领声明（Claim Ledger）

> 用途：在进入执行前先声明 TODO 负责人与范围，避免多人并行冲突。  
> 规则：同一 TODO Scope 同时仅允许一个 `planned/active` 认领；到期需续期或回退 `planned`。
> Owner 来源：历史 claim 的 owner 继承自已登记记录（2026-03-02 起）；新拆分但未分配的 claim，`Owner` 保持为空。
> 完整性口径：`T5-*`（AgentScope 补齐项）在本表仅维护项目级聚合认领；详细切片与执行状态以 `docs/todos/agentscope_domain_execution_todos.md` 为唯一来源，本表通过 `Detail Claim Ref` 对账。
> 状态口径：`TODO` 条目与 Claim Ledger 统一使用 `planned/active/done/deprecated`。

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Detail Claim Ref | Notes |
|---|---|---|---|---|---|---|---|---|
| CLM-20260302-AG1 | T5-2 | lang | done | 2026-03-02 | 2026-03-03 | `agentscope-d2-d4-thinking-transport` | `CLM-20260302-D2D4` | D2/D4 已完成实现与回归，待补归档/门禁链接。 |
| ~~CLM-20260302-AG2~~ | ~~T2-1~~ | ~~lang~~ | ~~deprecated~~ | ~~2026-03-02~~ | ~~2026-03-03~~ | ~~`agentscope-d5-safe-compression`~~ | ~~`CLM-20260302-D5`~~ | D5 已在 PR #136 合入；该历史 claim 已废弃，不再作为当前认领入口。 |
| CLM-20260302-AG3 | T5-5（D7 子范围） | lang | done | 2026-03-02 | 2026-03-03 | `agentscope-d7-plan-state-tools` | `CLM-20260302-D7` | PR #138 已合入主干，D7 子范围执行闭环完成。 |
| ~~CLM-20260302-AG4~~ | ~~T5-3（历史聚合）~~ | ~~lang~~ | ~~deprecated~~ | ~~2026-03-02~~ | ~~2026-03-04~~ | ~~`agentscope-d1-d3-message-pipeline`~~ | ~~`CLM-20260302-D1D3`~~ | 历史聚合认领已废弃；后续以 AG6（TODO 级 claim）为准。 |
| ~~CLM-20260303-AG5~~ | ~~T5-4（历史聚合）~~ | ~~N/A~~ | ~~deprecated~~ | ~~2026-03-03~~ | ~~2026-03-04~~ | ~~`pending`~~ | ~~`CLM-20260303-D6D8`~~ | 聚合占位 claim 已废弃；后续以 AG7（TODO 级 claim）为准。 |
| CLM-20260304-AG6 | T5-3 |  | planned | 2026-03-04 | 2026-03-11 | `agentscope-d1-d3-message-pipeline` | `CLM-20260304-D1 + CLM-20260304-D3` | TODO 级认领；切片仅在 AgentScope 详细区维护。 |
| CLM-20260304-AG7 | T5-4 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `CLM-20260304-D6 + CLM-20260304-D8` | TODO 级认领；切片仅在 AgentScope 详细区维护。 |
| CLM-20260304-AG8 | T1-2 + T1-5 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | 项目层高复杂 TODO 组待分配；切片见详细拆分区。 |
| CLM-20260304-AG9 | T2-3 + T2-4 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | 项目层治理 TODO 组待分配；切片见详细拆分区。 |
| CLM-20260304-AG10 | T0-6 | lang | done | 2026-03-04 | 2026-03-11 | `pending` | `—` | `search_file` 路径契约回归已修复并回归通过。 |
| CLM-20260304-AG11 | T0-4 + T0-5 | lang | active | 2026-03-04 | 2026-03-11 | `pending` | `—` | T0-5 已完成首版映射与 CI 巡检；T0-4 facade 合规收尾中。 |
| CLM-20260304-AG12 | T1-3 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | P1 未完成项补齐认领声明：`ISecurityBoundary` 接入待分配。 |
| CLM-20260304-AG13 | T2-1（剩余范围） + T2-2 + T5-1 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | Layer-2 策略补齐：D5 子范围已完成，剩余上下文融合/多阶段 prompt/session 补齐待分配。 |
| CLM-20260304-AG14 | T3-1 + T3-2 + T3-3 + T3-4 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | Layer-3 工程化与文档治理未完成项补齐认领声明。 |
| CLM-20260304-AG15 | T4-2 + T4-3 |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | 运行期配置统一与默认可观测采集持久化未完成项补齐认领声明。 |
| CLM-20260304-AG16 | T5-5（剩余范围，D7 子范围外） |  | planned | 2026-03-04 | 2026-03-11 | `pending` | `—` | D7 子范围已由 `AG3/CLM-20260302-D7` 闭环；本条仅覆盖剩余范围，暂无明细 claim。 |

对账快照（2026-03-04）：
- AgentScope 聚合 claim（AG1/AG2/AG3/AG6/AG7）均可在 `agentscope_domain_execution_todos.md` 中找到明细 claim 对应。
- 项目层独立 claim（AG8/AG9/AG10/AG11/AG12/AG13/AG14/AG15/AG16）不在 AgentScope 明细板拆分。

## 2. 当前基线

- 测试基线（2026-03-04）：`.venv/bin/pytest -q` => `676 passed, 12 skipped, 1 warning`。
- 关键问题聚类：
  - 全量 TODO / Claim / Feature 状态存在漂移（已 merge 或 archived 的 change 仍标记 active/draft）。
  - 若干 package `__init__.py` 不满足 facade 约束。
- 设计已定义但实现未闭环：plan attempt 隔离（snapshot/rollback）、Context 检索融合、完整 HITL 语义、P0 conformance gate 与治理自动化门禁。

## 3. 优先级路线图

## P0 运行基线与契约一致性

- [x] T0-1 修复当前失败测试，恢复主干健康基线。  
  Status: `done`  
  Evidence: `.venv/bin/pytest -q` => `504 passed, 12 skipped, 1 warning`；`.venv/bin/pytest -q tests/unit/test_dare_agent_security_boundary.py::test_tool_loop_approval_evaluate_exception_returns_structured_failure tests/unit/test_dare_agent_security_boundary.py::test_tool_loop_approval_wait_exception_returns_structured_failure` => `2 passed`；`dare_framework/tool/_internal/governed_tool_gateway.py`（审批异常语义回归修复）  
  Last Updated: `2026-03-01`
- [x] T0-2 统一 `ResourceAction` 与 action handler 动作契约。  
  Status: `done`  
  Evidence: `dare_framework/transport/_internal/adapters.py`（`/approvals list` 规范化为 `approvals:list`，并提取审批 action 参数）；`tests/unit/test_transport_adapters.py`（新增契约回归）；`.venv/bin/pytest -q tests/unit/test_transport_adapters.py tests/unit/test_interaction_dispatcher.py tests/unit/test_transport_channel.py tests/integration/test_client_cli_flow.py` => `33 passed, 1 warning`  
  Last Updated: `2026-03-01`
- [x] T0-3 统一 CLI 对 `invoke(action, **params)` 的调用方式。  
  Status: `done`  
  Evidence: `examples/05-dare-coding-agent-enhanced/cli.py`、`examples/06-dare-coding-agent-mcp/cli.py`（`_invoke_approval_action` 统一为 `invoke(action, **params)` 形态，移除 `params={...}` 调用分叉）；`tests/unit/test_examples_cli.py`、`tests/unit/test_examples_cli_mcp.py`（新增 kwargs 调用契约回归）  
  Commands: `.venv/bin/pytest -q tests/unit/test_examples_cli.py tests/unit/test_examples_cli_mcp.py` => `22 passed, 1 warning`  
  Last Updated: `2026-03-01`
- [ ] T0-4 修复 `__init__.py` facade 违规并固化回归检查。
  Status: `planned`
- [x] T0-5 建立“失败测试 -> 责任模块 -> owner”映射并例行巡检。
  Status: `done`
  Evidence: `scripts/ci/p0_gate.py`（category summary 新增 `owner`）；`scripts/ci/check_test_failure_ownership.py`（映射完整性巡检脚本）；`.github/workflows/ci-gate.yml`（新增 `failure-ownership-map` job）；`docs/guides/P0_Gate_Runbook.md`（命令与排障入口更新）；`.venv/bin/python -m pytest -q tests/unit/test_p0_gate_ci.py tests/unit/test_check_test_failure_ownership.py` => `7 passed`
  Last Updated: `2026-03-04`
- [x] T0-6 修复 `search_file` 输出路径契约回归（绝对路径 vs 相对路径）。  
  Status: `done`  
  Evidence: `.venv/bin/pytest -q tests/unit/test_v4_file_tools.py::test_search_file_finds_matching_paths` => `1 passed`；`.venv/bin/pytest -q` => `676 passed, 12 skipped, 1 warning`  
  Last Updated: `2026-03-04`

验收：

- 默认开发环境 `pytest` 稳定通过。
- P0 问题均有回归测试。

## P1 核心架构闭环（对齐权威设计）

- [x] T1-1 将 `ValidatedPlan.steps` 真正接入 Execute Loop。  
  Status: `done`  
  Evidence: `openspec/changes/p0-step-driven-execution/tasks.md`；`dare_framework/agent/_internal/execute_engine.py`；`dare_framework/agent/dare_agent.py`；`.venv/bin/pytest -q tests/unit/test_dare_agent_step_driven_mode.py tests/unit/test_dare_agent_orchestration_split.py` => `27 passed`  
  Last Updated: `2026-03-01`
- [ ] T1-2 完成 plan attempt 隔离（snapshot/rollback）闭环。
  Status: `planned`
- [ ] T1-3 接入 `ISecurityBoundary`（trust derivation + policy gate）。
  Status: `planned`
- [x] T1-4 提供 EventLog 默认实现并接入 builder 推荐路径。  
  Status: `done`  
  Evidence: `openspec/changes/p0-default-eventlog/tasks.md`；`dare_framework/event/_internal/sqlite_event_log.py`；`dare_framework/agent/builder.py`；`dare_framework/agent/dare_agent.py`；`dare_framework/observability/_internal/event_trace_bridge.py`；`.venv/bin/pytest -q tests/unit/test_event_sqlite_event_log.py tests/unit/test_builder_security_boundary.py tests/unit/test_five_layer_agent.py` => `43 passed`  
  Last Updated: `2026-03-01`
- [ ] T1-5 完成 HITL 语义闭环（pause -> wait -> resume）。
  Status: `planned`

验收：

- 架构不变量有代码与测试证据。
- 关键示例可复现实验结论。

## P2 上下文工程与治理能力

- [ ] T2-1 落地 STM/LTM/Knowledge 融合策略（含预算归因）。
  Status: `planned`
- [ ] T2-2 落地多阶段 prompt（plan/execute/verify）与预算联动。
  Status: `planned`
- [ ] T2-3 统一 tool defs schema 与风险等级映射。
  Status: `planned`
- [ ] T2-4 打通审批记忆、风险模型与策略引擎。
  Status: `planned`

## P3 工程化与文档治理

- [ ] T3-1 收敛文档重复描述与冲突叙述。
  Status: `planned`
- [ ] T3-2 固化“实现视图 vs 设计视图”差异模板。
  Status: `planned`
- [ ] T3-3 降低 legacy/archived 测试占比，补 canonical 覆盖。
  Status: `planned`
- [ ] T3-4 固化质量门禁：`ruff` / `black --check` / `mypy --strict` / `pytest`。
  Status: `planned`

## 4. 任务拆分（依赖关系 × 重要程度 × 复杂度）

### 4.0 编号治理（去重后）

1. `T*`：项目级主清单编号，仅在本文件维护优先级、阶段与里程碑状态。
2. `D*`：AgentScope domain 编号，仅在 `docs/todos/agentscope_domain_execution_todos.md` 维护子任务状态与依赖。
3. `WP*`：不再作为独立编号维护；AgentScope 细切统一使用 `D*_a/b/c`。
4. 同一工作项不得在 `T*` 和 `D*` 两侧重复维护“子切片状态”。

### 4.1 项目层分层（T 编号）

| 分层 | 目标 | 重要程度 | 复杂度 | 关键依赖 | 关联 T |
|---|---|---|---|---|---|
| Layer-0 基线阻塞层 | 清零当前红灯，恢复可持续开发基线 | P0 | 中 | 无 | `T0-4` `T0-5` `T0-6` |
| Layer-1 运行时闭环层 | 关闭核心架构缺口 | P1 | 高 | Layer-0 | `T1-2` `T1-3` `T1-5` |
| Layer-2 治理能力层 | 收敛上下文/策略/记忆治理能力 | P1/P2 | 高 | Layer-1 | `T2-1` `T2-2` `T2-3` `T2-4` `T5-1` |
| Layer-3 工程化层 | 质量门禁与文档治理闭环 | P2/P3 | 中-高 | Layer-0~2 | `T3-1` `T3-2` `T3-3` `T3-4` `T4-2` `T4-3` `T5-5` |
| Layer-AS AgentScope 专项层 | 多模态输入与权限/观测链路 | P1/P2 | 高 | Gate-1 / Gate-3（按 D 域冻结） | `T5-3` `T5-4` |

### 4.2 T 与 D 映射（单向引用，避免重叠跟踪）

| 项目级 T | AgentScope 域映射 | 详细拆分位置 | 状态口径来源 |
|---|---|---|---|
| `T5-2` | `D2 + D4` | `docs/todos/agentscope_domain_execution_todos.md` | AgentScope 清单的 `Claim Ledger` + `D*` 状态 |
| `T2-1` | `D5` | `docs/todos/agentscope_domain_execution_todos.md` | AgentScope 清单的 `Claim Ledger` + `D*` 状态 |
| `T5-3` | `D1 + D3` | `docs/todos/agentscope_domain_execution_todos.md`（`D1_a/b/c`，`D3_a/b/c`） | AgentScope 清单的 `Claim Ledger` + `D*` 状态 |
| `T5-4` | `D6 + D8` | `docs/todos/agentscope_domain_execution_todos.md`（`D6_a/b/c`，`D8_a/b/c`） | AgentScope 清单的 `Claim Ledger` + `D*` 状态 |
| `T5-5`（AgentScope 范围） | `D7` | `docs/todos/agentscope_domain_execution_todos.md` | AgentScope 清单的 `Claim Ledger` + `D*` 状态 |

说明：本文件只维护上述 `T*` 的“是否进入下一阶段”结果，不维护 `D*` 子切片进度。
AgentScope 补齐详细 TODO 入口：`docs/todos/agentscope_domain_execution_todos.md`（单一详细来源）。

### 4.3 强依赖/高复杂拆分规则（项目层）

以下条件任一满足，必须拆分为子切片后再认领：
1. 存在明确上游冻结依赖（schema/payload/policy 字段未冻结时下游无法稳定开发）。
2. 预计跨 3 个及以上核心目录（例如 `agent/context/tool/transport/observability`）改动。
3. 同时包含“行为变更 + 契约变更 + 回归门禁”三类交付。
4. 若任务已映射到 AgentScope `D*`，拆分只在 AgentScope 清单执行，不在本文件重复拆分。

### 4.4 项目层需独立拆分的复杂项（非 AgentScope）

| 父任务 | 子切片 ID | 子切片范围 | 依赖 | 复杂度 |
|---|---|---|---|---|
| `T1-2` plan attempt 隔离 | `T1-2_a` | snapshot 持久化与回滚点定义 | Layer-0 | 中 |
| `T1-2` plan attempt 隔离 | `T1-2_b` | execute/verify 失败回滚路径接入 | `T1-2_a` | 高 |
| `T1-2` plan attempt 隔离 | `T1-2_c` | 回滚一致性回归与证据补齐 | `T1-2_b` | 中 |
| `T1-5` HITL 语义闭环 | `T1-5_a` | pause/wait/resume 状态机与错误语义 | Layer-1 | 高 |
| `T1-5` HITL 语义闭环 | `T1-5_b` | `plan/tool` 双入口语义对齐 | `T1-5_a` | 高 |
| `T1-5` HITL 语义闭环 | `T1-5_c` | HITL 端到端回归与运维排障说明 | `T1-5_b` | 中 |
| `T2-3` tool defs 与风险映射 | `T2-3_a` | tool defs schema 统一 | Layer-1 | 高 |
| `T2-3` tool defs 与风险映射 | `T2-3_b` | risk level 到 policy 映射 | `T2-3_a` | 高 |
| `T2-4` 审批记忆与策略引擎 | `T2-4_a` | approval memory 数据面统一 | `T2-3_b` | 高 |
| `T2-4` 审批记忆与策略引擎 | `T2-4_b` | policy 决策链路与审计证据联动 | `T2-4_a` | 高 |

### 4.5 阶段化执行编号（用于派工）

| 阶段 | 编号 | 对应切片 | 目标 |
|---|---|---|---|
| 第一阶段（阻塞清零 + 契约冻结） | `a` | `T0-6` | 修复红灯用例，恢复全量基线入口 |
| 第一阶段（阻塞清零 + 契约冻结） | `b` | `T0-4` + `T0-5` | facade 合规 + 失败映射责任化 |
| 第一阶段（阻塞清零 + 契约冻结） | `c1` | `T5-3`（执行看 `D1_a/b/c`） | 多模态输入协议冻结（Gate-1） |
| 第一阶段（阻塞清零 + 契约冻结） | `c2` | `T2-3_a` | tool defs schema 统一 |
| 第一阶段（阻塞清零 + 契约冻结） | `c3` | `T2-3_b` | risk level 与 policy 映射冻结 |
| 第二阶段（核心闭环实现） | `d` | `T1-2_a` + `T1-2_b` + `T1-2_c` | plan attempt 隔离闭环 |
| 第二阶段（核心闭环实现） | `e1` | `T1-5_a` + `T1-5_b` | HITL 语义状态机与双入口对齐 |
| 第二阶段（核心闭环实现） | `e2` | `T2-4_a` + `T2-4_b` | 审批记忆与策略引擎联动 |
| 第二阶段（核心闭环实现） | `f` | `T5-4`（执行看 `D6_a/b/c`） | 权限与审计链路冻结（Gate-3） |
| 第三阶段（治理与发布门禁） | `g` | `T3-1` + `T3-2` | 文档冲突收敛 + 差异模板固定 |
| 第三阶段（治理与发布门禁） | `h1` | `T3-3` + `T3-4` | 测试结构治理 + 质量门禁 CI 固化 |
| 第三阶段（治理与发布门禁） | `h2` | `T5-5` + 治理门禁清单 | 架构设计收口与证据门禁闭环 |

## 5. 维护规则

- 每次架构级评审或里程碑后更新本清单。
- 每个 `done` 项必须附带 evidence。
- 与模块 TODO 或权威设计冲突时，以权威设计与最新实现证据为准，并在 24 小时内完成同步更新。

## 6. 补充关注点（本地 stash 恢复）

以下事项来自本地未跟踪版本，作为跨阶段补充跟踪项保留：

- [x] T4-1 会话上下文自动压缩与跨会话交接闭环（已并入 T5-1）  
  Status: `done`  
  说明：与 T5-1 合并，后续以 T5-1 作为唯一执行入口；本项仅保留追溯。  
  Evidence: `dare_framework/context/context.py`, `dare_framework/compression/core.py`, `dare_framework/plan/types.py`

- [ ] T4-2 运行期配置统一收敛（含配额/预算）  
  Status: `planned`  
  现状：模型/MCP/工具等大量配置来自 `Config`；但预算上限（tokens/cost/tool_calls/time）主要通过 `with_budget(Budget)` 注入，`Config` 当前无预算字段，未形成“全走 config”统一面。  
  Evidence: `dare_framework/config/types.py`, `dare_framework/agent/builder.py`, `dare_framework/context/types.py`

- [ ] T4-3 元信息统计默认可采集、可持久化、可查询  
  Status: `planned`  
  现状：token 与 tool 调用在运行中有统计；Observability 模块可采集 metrics/traces，但默认是 no-op，且并非默认持久化输出，API 调用层面的统一报表能力仍需收敛。  
  Evidence: `dare_framework/agent/dare_agent.py`, `dare_framework/observability/_internal/tracing_hook.py`, `dare_framework/observability/_internal/metrics_collector.py`

- [x] T4-4 图片/富媒体一等支持（模型输入与上下文链路，已并入 T5-3）  
  Status: `done`  
  说明：与 T5-3 合并，后续以 T5-3 作为唯一执行入口；本项仅保留追溯。  
  Evidence: `dare_framework/context/types.py`, `dare_framework/model/adapters/openai_adapter.py`, `dare_framework/a2a/server/message_adapter.py`

## 7. 本次新增事项（2026-02-25）

- [ ] T5-1 session 管理下 context 持久化与跨会话交接闭环  
  Status: `planned`  
  范围：补齐 session 生命周期内/跨 session 的 context 读写、恢复、版本化与兼容策略（含失败回滚与迁移策略）；统一接入 context 自动压缩与 session summary 交接链路。  
  交付：最小可用持久化方案 + 回归测试 + 运维排障说明。

- [x] T5-2 工具调用与 LLM thinking 通过 transport send 输出（含消息类型枚举）  
  Status: `done`  
  范围：tool call 中间态、LLM thinking/trace 信息通过统一 transport 通道输出，消息类型枚举与序列化协议已对齐。  
  交付：端到端消息流测试（sender/transport/receiver）+ 向后兼容策略。  
  Evidence：`openspec/changes/archive/2026-03-03-agentscope-d2-d4-thinking-transport/`，`docs/features/agentscope-d2-d4-thinking-transport.md`，`.venv/bin/pytest -q`（`528 passed, 12 skipped, 1 warning`）  
  Last Updated: `2026-03-03`

- [ ] T5-3 图片/音频/视频富媒体消息格式支持  
  Status: `planned`  
  范围：定义并落地多模态 message schema（文本 + 图片 + 音频 + 视频），覆盖模型输入、上下文存储、transport 传输与适配器能力探测；统一替代“图片/富媒体一等支持”的原 T4-4 范围（含 A2A 附件链路规范化）。  
  交付：跨适配器能力矩阵 + 不支持能力时的降级策略 + 示例用例。

- [ ] T5-4 全链路日志输出整理（模块分层与规范化）  
  Status: `planned`  
  范围：收敛 agent/context/tool/model/transport 等关键路径日志，统一字段、级别、trace/session 关联键与脱敏规则。  
  交付：日志规范文档 + 关键流程日志覆盖检查脚本 + 采样策略说明。

- [ ] T5-5 完整架构设计与各 domain 详细设计补齐  
  Status: `planned`  
  说明：`D7` 子范围已 `done`（对应 `AG3/CLM-20260302-D7`），当前跟踪剩余范围。  
  范围：补齐整体目标架构与 domain 设计文档，至少覆盖关键 API、数据模型、核心流程、异常处理、边界条件与可观测性策略。  
  交付：架构总览文档 + 分 domain 设计文档包 + 设计评审清单与验收标准。

## 8. 文档先行治理专项（2026-02-27）

- [x] T6-1 按基线 gap 分析推进修复与回写
  Status: `done`
  范围：基于 `docs/todos/archive/2026-02-27_design_code_gap_analysis.md` 与 `docs/todos/archive/2026-02-27_design_code_gap_todo.md`，逐项按 OpenSpec 执行。
  交付：DG 系列 TODO 状态回写 + OpenSpec 任务证据 + 文档归档记录。  
  Evidence：`openspec/changes/archive/2026-02-27-*`，`docs/todos/archive/2026-02-27_design_code_gap_todo.md`

- [x] T6-2 执行一次完整设计文档 review（非最小补充）
  Status: `done`
  范围：覆盖 `docs/design/Architecture.md` 与 `docs/design/modules/*/README.md`，修正与实现冲突的状态断言，并收敛 security canonical 导入路径。
  交付：full review gap 分析 + TODO 清单 + 对应实现/文档修复。  
  Evidence：`docs/todos/archive/2026-02-27_full_design_review_gap_analysis.md`，`docs/todos/archive/2026-02-27_full_design_review_gap_todo.md`，`dare_framework/security/__init__.py`

- [x] T6-3 推进“按文档可重建”治理闭环（P0/P1）
  Status: `done`
  范围：基于可重建性 gap 分析，优先补齐追踪矩阵、审批语义决策表、重建 SOP 三项 P0。
  交付：`docs/todos/archive/2026-02-27_design_reconstructability_gap_analysis.md` + `docs/todos/archive/2026-02-27_design_reconstructability_gap_todo.md` 对应事项回写完成。  
  Evidence：`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/`，`docs/design/Design_Reconstructability_Traceability_Matrix.md`，`docs/guides/Design_Reconstruction_SOP.md`

- [x] T6-4 补齐模块级测试锚点与 embedding 最小测试基线
  Status: `done`
  范围：基于 full review 第二轮结论，为 `docs/design/modules/*/README.md` 补齐测试锚点；为 embedding 域补最小单测并回写文档证据。
  交付：`docs/todos/archive/2026-02-27_full_design_review_gap_todo.md` 中 FR-009/FR-011 状态闭环。
  Evidence：`docs/todos/archive/2026-02-27_full_design_review_gap_analysis.md`，`docs/todos/archive/2026-02-27_full_design_review_gap_todo.md`，`tests/unit/test_embedding_openai_adapter.py`

- [x] T6-5 补 memory/knowledge 域直连单测并替换过渡声明
  Status: `done`
  范围：关闭 FR-GAP-011，对 `memory/knowledge` 域补齐直连单测，移除当前“组合验证锚点 + 缺失声明”的过渡状态。
  交付：`docs/todos/archive/2026-02-27_full_design_review_gap_todo.md` 中 FR-012 状态闭环。
  Evidence：`docs/todos/archive/2026-02-27_full_design_review_gap_analysis.md`，`docs/todos/archive/2026-02-27_full_design_review_gap_todo.md`，`tests/unit/test_memory_knowledge_direct.py`
