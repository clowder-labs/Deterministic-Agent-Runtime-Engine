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

### Requirement: Milestone 自动拆分能力（LLM Decomposition）

The system SHALL provide an `IPlanner.decompose(task, ctx)` method that decomposes a `Task` into a list of `Milestone` objects, enabling LLM-driven automatic task decomposition.

- `decompose` MUST return a `DecompositionResult` containing `milestones` list and `reasoning` string.
- If `Task.milestones` is already populated, decomposition SHOULD be skipped.
- A default implementation SHALL return a single milestone derived from `task.description`.

#### Scenario: LLM decomposes complex task

- **GIVEN** a Task with empty milestones and a configured LLM planner
- **WHEN** `IPlanner.decompose(task, ctx)` is called
- **THEN** the planner returns multiple Milestones with distinct descriptions and success_criteria

#### Scenario: Simple task uses single milestone

- **GIVEN** a Task with empty milestones and default planner
- **WHEN** `IPlanner.decompose(task, ctx)` is called
- **THEN** a single Milestone is returned with description matching task.description

#### Scenario: Pre-defined milestones skip decomposition

- **GIVEN** a Task with pre-defined milestones
- **WHEN** Session Loop initializes
- **THEN** `decompose` is NOT called and pre-defined milestones are used

---

### Requirement: 结构化证据收集与验证（Evidence Closure）

The system SHALL provide structured evidence collection and mandatory verification against milestone success criteria.

- `Evidence` dataclass MUST include: `evidence_id`, `evidence_type`, `source`, `data`, `timestamp`.
- `VerifyResult` MUST be extended with `evidence_required` and `evidence_collected` fields.
- `IValidator.verify_milestone` SHOULD check that collected evidence satisfies success_criteria.
- Tool results SHOULD automatically produce `Evidence` entries with `evidence_type="tool_result"`.

#### Scenario: Tool result produces evidence

- **GIVEN** a tool invocation via `IToolGateway.invoke()`
- **WHEN** the tool returns a result
- **THEN** an `Evidence` object is created with type "tool_result" and added to milestone state

#### Scenario: Milestone verification checks evidence

- **GIVEN** a Milestone with success_criteria ["file_created", "tests_pass"]
- **WHEN** `verify_milestone` is called with collected evidence
- **THEN** the validator checks evidence against criteria and returns success only if all criteria are satisfied

#### Scenario: Missing evidence causes verification failure

- **GIVEN** a Milestone with success_criteria ["api_response_200"]
- **WHEN** `verify_milestone` is called with no matching evidence
- **THEN** the validator returns `success=False` with error indicating missing evidence

---

### Requirement: DecompositionResult 类型定义

The plan module SHALL provide a `DecompositionResult` type to carry milestone decomposition output.

- `DecompositionResult` MUST contain: `milestones: list[Milestone]`, `reasoning: str`, `metadata: dict`.
- The type MUST be immutable (frozen dataclass).

#### Scenario: Access decomposition result

- **WHEN** a decomposition is performed
- **THEN** the result provides milestones list and reasoning string for auditability

### Requirement: Step-driven Execute Loop consumes validated steps

When runtime execution mode is `step_driven`, the system SHALL execute `ValidatedPlan.steps` sequentially through `IStepExecutor` instead of invoking the model-driven execute loop.

#### Scenario: Step-driven execution runs validated steps in order

- **GIVEN** a `ValidatedPlan` with ordered steps
- **AND** a configured `IStepExecutor`
- **WHEN** `DareAgent` runs execute loop in `step_driven` mode
- **THEN** each step is executed in sequence via `IStepExecutor.execute_step(...)`
- **AND** the returned step outputs are included in execute result outputs

#### Scenario: Missing plan fails fast in step-driven mode

- **GIVEN** `execution_mode` is `step_driven`
- **WHEN** execute loop is called without a validated plan
- **THEN** the runtime returns failure
- **AND** the error clearly indicates step-driven mode requires a validated plan

#### Scenario: Empty validated steps fail fast in step-driven mode

- **GIVEN** `execution_mode` is `step_driven`
- **AND** a validated plan with no steps
- **WHEN** execute loop starts
- **THEN** the runtime returns failure
- **AND** the error clearly indicates validated steps are required
