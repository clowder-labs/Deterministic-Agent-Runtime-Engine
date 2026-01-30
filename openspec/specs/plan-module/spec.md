# plan-module Specification

## Purpose
TBD - created by archiving change update-plan-module-v4. Update Purpose after archive.
## Requirements
### Requirement: 计划模型分层（Proposed vs Validated）
计划模块 SHALL 提供明确的 Proposed/Validated 类型分层：
- Proposed 计划与步骤来自 planner，视为不可信输入。
- Validated 计划与步骤由 validator 基于可信 registry 派生，至少包含可信 `risk_level`；其余可信字段统一承载在可信 `metadata` 中，且不与 Proposed 类型混用或别名化。

#### Scenario: 读取计划类型分层
- **WHEN** 贡献者查看 plan 模型
- **THEN** ProposedPlan/ProposedStep 与 ValidatedPlan/ValidatedStep 为独立类型，且 ValidatedStep 明确携带可信字段

### Requirement: 计划尝试的可审计信息承载
计划模块 SHALL 提供足够字段以记录计划尝试：
- ProposedPlan 包含 `attempt` 与 `metadata` 以支持 `plan.attempt` 事件记录。
- ValidatedPlan 包含 `success` 与 `errors` 以支持 `plan.validated/plan.invalid` 事件记录。

#### Scenario: 无效计划仅记录尝试元信息
- **WHEN** validator 返回 `success=false`
- **THEN** 运行时可记录 attempt 元信息与错误，并且无效计划步骤不会作为外层状态持久化

### Requirement: 计划策略接口语义
计划模块 SHALL 定义 `IPlanner`、`IValidator`、`IRemediator` 及其 manager 接口，并满足如下语义：
- `IPlanner.plan(ctx)` 返回 `ProposedPlan`。
- `IValidator.validate_plan(plan, ctx)` 返回 `ValidatedPlan`，且通过 `success/errors` 表示是否通过验证。
- `IValidator.verify_milestone(result, ctx)` 返回 `VerifyResult`。
- `IRemediator.remediate(verify_result, ctx)` 返回可写入反思的文本。

#### Scenario: Planner 返回 ProposedPlan
- **WHEN** 调用 `IPlanner.plan(ctx)`
- **THEN** 返回包含 `plan_description` 与有序 `steps` 的 ProposedPlan

### Requirement: 计划步骤与 Tool Loop 执行边界
计划模块 SHALL 提供 `Envelope`、`DonePredicate`、`ToolLoopRequest` 模型，以支撑 Tool Loop 的执行边界：
- `Envelope` 至少包含 `allowed_capability_ids`、`budget`、`done_predicate`、`risk_level`。
- `ToolLoopRequest` 由 `capability_id + params + envelope` 组成。
- `ValidatedStep` 可在可信 `metadata` 中携带由 registry 派生的 `capability_kind` 等字段，以支持 Plan Tool 识别。

#### Scenario: ToolLoopRequest 受 Envelope 约束
- **GIVEN** 一个包含 `allowed_capability_ids` 的 Envelope
- **WHEN** 从 ValidatedStep 生成 ToolLoopRequest
- **THEN** 调用仅允许发生在该 allowlist 范围内

