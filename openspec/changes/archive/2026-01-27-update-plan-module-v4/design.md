## 背景
- V4 设计文档（`docs/design/Architecture.md`、`docs/design/Interfaces.md`）明确了五层循环、Plan Attempt Isolation、Plan Tool 语义与可信元数据派生规则。
- 当前 `dare_framework/plan` 已具备基础类型与接口，但缺少一份明确的规格与边界说明，导致计划模块如何承载“可信/不可信分层”与“失败计划隔离”等核心语义仍不够清晰。

## 目标 / 非目标
### 目标
- 以 V4 设计为准，补齐 plan 模块的数据模型与策略接口规范。
- 明确 Proposed/Validated 分层与可信元数据派生的职责边界。
- 明确 plan 与 tool/security/event 的交互边界，便于审计与复验。

### 非目标
- 不实现具体规划算法或 LLM 提示词策略。
- 不改变五层循环的既有高层语义（由 `core-runtime` 规格负责）。
- 不在本阶段引入新的外部依赖或持久化存储。

## 关键决策
1. **Plan 领域遵循 V4 目录约定**
   - `types.py` 仅承载数据模型；`interfaces.py` 承载可插拔策略；`kernel.py` 作为稳定合同入口；默认实现放在 `_internal/`。

2. **Proposed vs Validated 分层**
   - Proposed 计划/步骤来源不可信（来自 planner），不得携带可信字段（如风险等级、审批要求、超时策略）。
   - Validated 计划/步骤由 validator + 可信 registry 派生，至少携带 `risk_level`；其余可信字段（`requires_approval`、`timeout_seconds`、`capability_kind`、`is_work_unit`）统一存放在可信 `metadata` 中。

3. **Envelope/ToolLoopRequest 作为执行边界**
   - 计划步骤可携带 `Envelope`（允许能力、预算、DonePredicate、风险级别），执行层必须以 `ToolLoopRequest` 作为调用载体。

4. **Plan Attempt Isolation 的数据承载**
   - `ProposedPlan` 包含 `attempt` 与 `metadata`，用于记录尝试与诊断信息。
   - 失败计划不进入外层状态，仅允许记录 attempt 元信息、错误与 remediation 产生的 reflection。

5. **Plan Tool 语义对齐**
   - 识别 Plan Tool 以 registry `capability_kind=plan_tool` 为主（兼容 `plan:` 前缀约定）。
   - Execute 遇到 Plan Tool 需回到 Plan Loop，此语义由运行时实现，但 plan 模块需保留其能力类型信息。

## 交互边界
- **Tool Registry / ToolGateway**：Validator 在验证阶段基于可信 registry 派生 `risk_level` 与相关元数据，禁止使用 planner 输出的风险字段。
- **Security Boundary**：Plan→Execute 阶段触发 `check_policy(action="execute_plan", ...)`；执行阶段对每个能力调用进行 `check_policy(action="invoke_capability", ...)`。
- **Event Log**：计划尝试与验证结果必须形成结构化事件（`plan.attempt` / `plan.validated` / `plan.invalid`），并带有关联标识（task/session/milestone）。

## 风险 / 权衡
- **字段粒度**：在 `ValidatedStep` 中强制加入全部可信元数据会增加迁移成本；以结构化字段 + `metadata` 的折中方式降低破坏性变更。
- **数据结构扩展**：本次不新增独立 `PlanAttempt` 结构体，计划尝试信息通过 `ProposedPlan.attempt/metadata` 与事件日志承载。
- **行为 vs 数据**：Plan Attempt Isolation 是运行时行为，但需要 plan 类型提供足够的可审计字段以支持验证与回放。

## 迁移计划
1. 对齐 plan 类型与接口（Proposed/Validated 分层、Envelope、VerifyResult/RunResult 等）。
2. 补齐 validator 的派生语义与事件日志字段（实现阶段）。
3. 对齐五层循环中的计划隔离与 Plan Tool 处理（实现阶段）。
4. 添加覆盖计划分层、验证失败隔离、计划工具回退的测试与验证。

## 开放问题
暂无（范围限定为 `dare_framework`；可信元数据统一放入 `metadata`；不新增 `PlanAttempt` 结构体）。
