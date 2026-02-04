# Module: plan

> Status: aligned to `dare_framework/plan` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 任务/计划/结果模型定义（Task / Milestone / Plan / RunResult）。
- Planner 生成 `ProposedPlan`，Validator 生成 `ValidatedPlan`，Remediator 生成反思。
- 定义 Tool Loop 的 `Envelope` 与 `DonePredicate`。

## 2. 关键概念与数据结构

- `Task`：用户任务输入，支持可选 milestones。
- `Milestone`：最小验证单元。
- `ProposedPlan` / `ValidatedPlan`：计划的非可信/可信两阶段表示。
- `ProposedStep` / `ValidatedStep`：计划步骤结构。
- `Envelope` / `DonePredicate`：工具调用边界与完成条件。
- `VerifyResult`：里程碑验证结果。

## 3. 关键接口与实现

- Planner：`IPlanner.plan(ctx) -> ProposedPlan`
- Validator：`IValidator.validate_plan(...) -> ValidatedPlan` / `verify_milestone(...) -> VerifyResult`
- Remediator：`IRemediator.remediate(...) -> str`
- 管理器接口：`IPlannerManager`, `IValidatorManager`, `IRemediatorManager`

默认实现：
- `DefaultPlanner`：基于 LLM 的 evidence-driven 计划（`dare_framework/plan/_internal/default_planner.py`）
- `RegistryPlanValidator`：从 ToolRegistry 推导可信元数据（`dare_framework/plan/_internal/registry_validator.py`）
- `DefaultRemediator`：基于 LLM 的反思文本（`dare_framework/plan/_internal/default_remediator.py`）
- `CompositeValidator`：多 validator 组合（`dare_framework/plan/_internal/composite_validator.py`）

## 4. 与 Agent 的交互（当前实现）

- DareAgent 在 Milestone Loop 中调用 planner + validator。
- 验证失败会记录 attempt；可选 remediator 输出反思。
- 验证成功后进入 Execute Loop。

> 现状差距：ValidatedPlan.steps 未驱动执行；Execute Loop 由模型自主决定工具调用（TODO）。

## 5. 约束与限制（当前实现）

- **计划隔离不足**：失败计划不会回滚 STM 或上下文状态（TODO）。
- **风险/审批未闭环**：Validator 可派生 `risk_level`，但未接入 policy gate（TODO）。
- **证据闭环未统一**：Planner 侧 evidence 与 ToolResult evidence 体系尚未完全对齐（TODO）。

## 6. 扩展点

- 自定义 Planner/Validator/Remediator。
- 使用 `RegistryPlanValidator` 组合自定义 Validator，实现可信元数据派生。
- 在 Execute Loop 中引入“计划驱动执行”策略（TODO）。

## 7. TODO / 未决问题

- TODO: 将 ValidatedPlan.steps 绑定工具执行（计划驱动）。
- TODO: 计划 attempt 隔离（Context snapshot / rollback）。
- TODO: 统一证据模型（planner evidence ↔ tool evidence）。
- TODO: 明确 plan tool 的元数据与 policy gate 语义。

## 8. Design Clarifications (2026-02-03)

- Doc/Impl gap: `plan/kernel.py` is empty; decide kernel surface or document interfaces-only.
- Type cleanup: internal validators/planners should avoid `Any` for core plan types.
