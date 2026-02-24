# DARE Framework 项目总体 TODO

> 更新时间：2026-02-24  
> 范围：项目全局演进（非单个 feature 的实现方案）

## 1. 目标与边界

- 目标：持续收敛 `docs/design` 目标架构与 `dare_framework/` 当前实现，优先保证可运行、可验证、可审计。
- 边界：这里只记录跨模块、跨阶段事项；具体任务拆解进入 OpenSpec 与模块文档。

## 2. 当前基线

- 测试基线（审查时）：`.venv/bin/pytest -q` => `8 failed, 202 passed, 13 skipped`。
- 关键问题聚类：
  - 交互动作枚举与 MCP action handler 契约不一致。
  - CLI 审批命令调用参数方式与 handler 签名不一致。
  - 内置 prompt 与测试约定不一致。
  - 若干 package `__init__.py` 不满足 facade 约束。
- 设计已定义但实现未闭环：`ISecurityBoundary` 接入、plan 驱动执行、EventLog 默认实现、Context 检索融合、完整 HITL 语义。

## 3. 优先级路线图

## P0 运行基线与契约一致性

- [ ] T0-1 修复当前失败测试，恢复主干健康基线。
- [ ] T0-2 统一 `ResourceAction` 与 action handler 动作契约。
- [ ] T0-3 统一 CLI 对 `invoke(action, **params)` 的调用方式。
- [ ] T0-4 修复 `__init__.py` facade 违规并固化回归检查。
- [ ] T0-5 建立“失败测试 -> 责任模块 -> owner”映射并例行巡检。

验收：

- 默认开发环境 `pytest` 稳定通过。
- P0 问题均有回归测试。

## P1 核心架构闭环（对齐权威设计）

- [ ] T1-1 将 `ValidatedPlan.steps` 真正接入 Execute Loop。
- [ ] T1-2 完成 plan attempt 隔离（snapshot/rollback）闭环。
- [ ] T1-3 接入 `ISecurityBoundary`（trust derivation + policy gate）。
- [ ] T1-4 提供 EventLog 默认实现并接入 builder 推荐路径。
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
