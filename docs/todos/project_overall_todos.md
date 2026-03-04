---
change_ids: []
doc_kind: todo
topics: ["project-roadmap", "governance", "todo"]
created: 2026-02-25
updated: 2026-03-04
status: active
---

# DARE Framework 项目总体 TODO

> 更新时间：2026-03-02  
> 范围：项目全局演进（非单个 feature 的实现方案）

## 1. 目标与边界

- 目标：持续收敛 `docs/design` 目标架构与 `dare_framework/` 当前实现，优先保证可运行、可验证、可审计。
- 边界：这里只记录跨模块、跨阶段事项；具体任务拆解进入 OpenSpec 与模块文档。

## 1.1 认领声明（Claim Ledger）

> 用途：在进入执行前先声明 TODO 负责人与范围，避免多人并行冲突。  
> 规则：同一 TODO Scope 同时仅允许一个 `planned/active` 认领；过期需续期或释放。

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-20260302-AG1 | T5-2 | zts212653 | active | 2026-03-02 | 2026-03-09 | `agentscope-d2-d4-thinking-transport` | 对齐 D2/D4：thinking + transport 事件链路（PR #134 review 中）。 |
| CLM-20260302-AG2 | T2-1 | zts212653 | active | 2026-03-02 | 2026-03-09 | `agentscope-d5-safe-compression` | 对齐 D5：安全压缩与预算收敛（PR #136 待审）。 |
| CLM-20260302-AG3 | D7-1~D7-4（关联 T5-5） | zts212653 | planned | 2026-03-02 | 2026-03-09 | `agentscope-d7-plan-state-tools` | 先按 AgentScope gap 切片推进 plan 状态机能力。 |
| CLM-20260302-AG4 | T5-3 | zts212653 | planned | 2026-03-02 | 2026-03-09 | `agentscope-d1-d3-message-pipeline` | 对齐 D1/D3：多模态输入 schema + normalize。 |

## 2. 当前基线

- 测试基线（审查时）：`.venv/bin/pytest -q` => `504 passed, 12 skipped, 1 warning`。
- 关键问题聚类：
  - 交互动作枚举与 transport slash-action 解析契约存在边界不一致（待持续回归监控）。
  - CLI 审批命令调用参数方式与 handler 签名不一致。
  - 内置 prompt 与测试约定不一致。
  - 若干 package `__init__.py` 不满足 facade 约束。
- 设计已定义但实现未闭环：`ISecurityBoundary` 接入、plan 驱动执行、EventLog 默认实现、Context 检索融合、完整 HITL 语义。

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
- [ ] T0-5 建立“失败测试 -> 责任模块 -> owner”映射并例行巡检。

验收：

- 默认开发环境 `pytest` 稳定通过。
- P0 问题均有回归测试。

## P1 核心架构闭环（对齐权威设计）

- [x] T1-1 将 `ValidatedPlan.steps` 真正接入 Execute Loop。  
  Status: `done`  
  Evidence: `openspec/changes/p0-step-driven-execution/tasks.md`；`dare_framework/agent/_internal/execute_engine.py`；`dare_framework/agent/dare_agent.py`；`.venv/bin/pytest -q tests/unit/test_dare_agent_step_driven_mode.py tests/unit/test_dare_agent_orchestration_split.py` => `27 passed`  
  Last Updated: `2026-03-01`
- [ ] T1-2 完成 plan attempt 隔离（snapshot/rollback）闭环。
- [ ] T1-3 接入 `ISecurityBoundary`（trust derivation + policy gate）。
- [x] T1-4 提供 EventLog 默认实现并接入 builder 推荐路径。  
  Status: `done`  
  Evidence: `openspec/changes/p0-default-eventlog/tasks.md`；`dare_framework/event/_internal/sqlite_event_log.py`；`dare_framework/agent/builder.py`；`dare_framework/agent/dare_agent.py`；`dare_framework/observability/_internal/event_trace_bridge.py`；`.venv/bin/pytest -q tests/unit/test_event_sqlite_event_log.py tests/unit/test_builder_security_boundary.py tests/unit/test_five_layer_agent.py` => `43 passed`  
  Last Updated: `2026-03-01`
- [ ] T1-5 完成 HITL 语义闭环（pause -> wait -> resume）。

验收：

- 架构不变量有代码与测试证据。
- 关键示例可复现实验结论。

## P2 上下文工程与治理能力

- [ ] T2-1 落地 STM/LTM/Knowledge 融合策略（含预算归因）。
- [ ] T2-2 落地多阶段 prompt（plan/execute/verify）与预算联动。
- [ ] T2-3 统一 tool defs schema 与风险等级映射。
- [ ] T2-4 打通审批记忆、风险模型与策略引擎。

## P3 工程化与文档治理

- [ ] T3-1 收敛文档重复描述与冲突叙述。
- [ ] T3-2 固化“实现视图 vs 设计视图”差异模板。
- [ ] T3-3 降低 legacy/archived 测试占比，补 canonical 覆盖。
- [ ] T3-4 固化质量门禁：`ruff` / `black --check` / `mypy --strict` / `pytest`。

## 4. 执行节奏建议

- Phase A（1-2 周）：优先完成 P0。
- Phase B（2-4 周）：推进 P1。
- Phase C（持续）：滚动推进 P2/P3。

## 5. 维护规则

- 每次架构级评审或里程碑后更新本清单。
- 每个 `done` 项必须附带 evidence。
- 与模块 TODO 或权威设计冲突时，以权威设计与最新实现证据为准，并在 24 小时内完成同步更新。

## 6. 补充关注点（本地 stash 恢复）

以下事项来自本地未跟踪版本，作为跨阶段补充跟踪项保留：

- [x] T4-1 会话上下文自动压缩与跨会话交接闭环（已并入 T5-1）  
  Status: `merged`  
  说明：与 T5-1 合并，后续以 T5-1 作为唯一执行入口；本项仅保留追溯。  
  Evidence: `dare_framework/context/context.py`, `dare_framework/compression/core.py`, `dare_framework/plan/types.py`

- [ ] T4-2 运行期配置统一收敛（含配额/预算）  
  Status: `todo`  
  现状：模型/MCP/工具等大量配置来自 `Config`；但预算上限（tokens/cost/tool_calls/time）主要通过 `with_budget(Budget)` 注入，`Config` 当前无预算字段，未形成“全走 config”统一面。  
  Evidence: `dare_framework/config/types.py`, `dare_framework/agent/builder.py`, `dare_framework/context/types.py`

- [ ] T4-3 元信息统计默认可采集、可持久化、可查询  
  Status: `doing`  
  现状：token 与 tool 调用在运行中有统计；Observability 模块可采集 metrics/traces，但默认是 no-op，且并非默认持久化输出，API 调用层面的统一报表能力仍需收敛。  
  Evidence: `dare_framework/agent/dare_agent.py`, `dare_framework/observability/_internal/tracing_hook.py`, `dare_framework/observability/_internal/metrics_collector.py`

- [x] T4-4 图片/富媒体一等支持（模型输入与上下文链路，已并入 T5-3）  
  Status: `merged`  
  说明：与 T5-3 合并，后续以 T5-3 作为唯一执行入口；本项仅保留追溯。  
  Evidence: `dare_framework/context/types.py`, `dare_framework/model/adapters/openai_adapter.py`, `dare_framework/a2a/server/message_adapter.py`

## 7. 本次新增事项（2026-02-25）

- [ ] T5-1 session 管理下 context 持久化与跨会话交接闭环  
  Status: `todo`  
  范围：补齐 session 生命周期内/跨 session 的 context 读写、恢复、版本化与兼容策略（含失败回滚与迁移策略）；统一接入 context 自动压缩与 session summary 交接链路。  
  交付：最小可用持久化方案 + 回归测试 + 运维排障说明。

- [ ] T5-2 工具调用与 LLM thinking 通过 transport send 输出（含消息类型枚举）  
  Status: `todo`  
  范围：将 tool call 中间态、LLM thinking/trace 信息通过统一 transport 通道发送；补齐并统一对应消息类型枚举与序列化协议。  
  交付：端到端消息流测试（sender/transport/receiver）+ 向后兼容策略。

- [ ] T5-3 图片/音频/视频富媒体消息格式支持  
  Status: `todo`  
  范围：定义并落地多模态 message schema（文本 + 图片 + 音频 + 视频），覆盖模型输入、上下文存储、transport 传输与适配器能力探测；统一替代“图片/富媒体一等支持”的原 T4-4 范围（含 A2A 附件链路规范化）。  
  交付：跨适配器能力矩阵 + 不支持能力时的降级策略 + 示例用例。

- [ ] T5-4 全链路日志输出整理（模块分层与规范化）  
  Status: `todo`  
  范围：收敛 agent/context/tool/model/transport 等关键路径日志，统一字段、级别、trace/session 关联键与脱敏规则。  
  交付：日志规范文档 + 关键流程日志覆盖检查脚本 + 采样策略说明。

- [ ] T5-5 完整架构设计与各 domain 详细设计补齐  
  Status: `todo`  
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
  Evidence：`docs/todos/2026-02-27_full_design_review_gap_analysis.md`，`docs/todos/2026-02-27_full_design_review_gap_todo.md`，`dare_framework/security/__init__.py`

- [x] T6-3 推进“按文档可重建”治理闭环（P0/P1）
  Status: `done`
  范围：基于可重建性 gap 分析，优先补齐追踪矩阵、审批语义决策表、重建 SOP 三项 P0。
  交付：`docs/todos/2026-02-27_design_reconstructability_gap_analysis.md` + `docs/todos/2026-02-27_design_reconstructability_gap_todo.md` 对应事项回写完成。  
  Evidence：`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/`，`docs/design/Design_Reconstructability_Traceability_Matrix.md`，`docs/guides/Design_Reconstruction_SOP.md`

- [x] T6-4 补齐模块级测试锚点与 embedding 最小测试基线
  Status: `done`
  范围：基于 full review 第二轮结论，为 `docs/design/modules/*/README.md` 补齐测试锚点；为 embedding 域补最小单测并回写文档证据。
  交付：`docs/todos/2026-02-27_full_design_review_gap_todo.md` 中 FR-009/FR-011 状态闭环。
  Evidence：`docs/todos/2026-02-27_full_design_review_gap_analysis.md`，`docs/todos/2026-02-27_full_design_review_gap_todo.md`，`tests/unit/test_embedding_openai_adapter.py`

- [x] T6-5 补 memory/knowledge 域直连单测并替换过渡声明
  Status: `done`
  范围：关闭 FR-GAP-011，对 `memory/knowledge` 域补齐直连单测，移除当前“组合验证锚点 + 缺失声明”的过渡状态。
  交付：`docs/todos/2026-02-27_full_design_review_gap_todo.md` 中 FR-012 状态闭环。
  Evidence：`docs/todos/2026-02-27_full_design_review_gap_analysis.md`，`docs/todos/2026-02-27_full_design_review_gap_todo.md`，`tests/unit/test_memory_knowledge_direct.py`
