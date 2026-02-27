## MODIFIED Requirements

### Requirement: 计划模型分层（Proposed vs Validated）
计划模块 SHALL 提供明确的 Proposed/Validated 类型分层：
- Proposed 计划与步骤来自 planner，视为不可信输入。
- Validated 计划与步骤由 validator 基于可信 registry 派生，至少包含可信 `risk_level`；其余可信字段统一承载在可信 `metadata` 中，且不与 Proposed 类型混用或别名化。

在支持 step-driven 执行时，`ValidatedStep` MUST 包含可直接执行所需的完整字段（`step_id`, `capability_id`, `params`, `envelope`）。

#### Scenario: 读取计划类型分层
- **WHEN** 贡献者查看 plan 模型
- **THEN** ProposedPlan/ProposedStep 与 ValidatedPlan/ValidatedStep 为独立类型，且 ValidatedStep 明确携带可信字段

#### Scenario: ValidatedStep 可直接执行
- **WHEN** 运行时进入 `step_driven` 执行模式
- **THEN** 每个 ValidatedStep 都可在无需二次推断的前提下交由 step executor 执行

### Requirement: 计划步骤与 Tool Loop 执行边界
计划模块 SHALL 提供 `Envelope`、`DonePredicate`、`ToolLoopRequest` 模型，以支撑 Tool Loop 的执行边界：
- `Envelope` 至少包含 `allowed_capability_ids`、`budget`、`done_predicate`、`risk_level`。
- `ToolLoopRequest` 由 `capability_id + params + envelope` 组成。
- `ValidatedStep` 可在可信 `metadata` 中携带由 registry 派生的 `capability_kind` 等字段，以支持 Plan Tool 识别。

在 `step_driven` 模式中，运行时 MUST 从 `ValidatedStep` 直接构建执行请求并执行，不依赖模型临时生成工具调用。

#### Scenario: ToolLoopRequest 受 Envelope 约束
- **GIVEN** 一个包含 `allowed_capability_ids` 的 Envelope
- **WHEN** 从 ValidatedStep 生成 ToolLoopRequest
- **THEN** 调用仅允许发生在该 allowlist 范围内

#### Scenario: Step-driven 不依赖模型二次选工具
- **GIVEN** 已通过验证的 `ValidatedPlan.steps`
- **WHEN** 运行时执行 `step_driven` 模式
- **THEN** 工具调用来源于 steps
- **AND** 不是由模型在执行期重新决定 capability

