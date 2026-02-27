## MODIFIED Requirements

### Requirement: Step-Driven Execution Mode
The runtime SHALL support a step-driven execution mode where the Execute Loop follows `ValidatedPlan.steps` sequentially.

- When `execution_mode="step_driven"`, the Execute Loop SHALL execute each `ValidatedStep` in order via `IStepExecutor`.
- Each step result SHALL be passed to the next step as context.
- If a step fails, execution SHALL halt and control returns to Milestone Loop for remediation.
- When `execution_mode="model_driven"` (default), the existing model-free execution behavior is preserved.
- In `step_driven` mode, runtime MUST NOT bypass validated step ordering by using ad-hoc model tool calls as the primary execution source.

#### Scenario: Step-by-step execution
- **GIVEN** a ValidatedPlan with 3 steps and `execution_mode="step_driven"`
- **WHEN** the Execute Loop runs
- **THEN** each step is executed in order, with previous results available to subsequent steps

#### Scenario: Step failure halts execution
- **GIVEN** a ValidatedPlan with 3 steps in step-driven mode
- **WHEN** step 2 fails
- **THEN** step 3 is NOT executed and control returns to Milestone Loop

#### Scenario: Model-driven mode preserves existing behavior
- **GIVEN** `execution_mode="model_driven"` (or not specified)
- **WHEN** the Execute Loop runs
- **THEN** the model drives execution freely without step constraints

### Requirement: IStepExecutor 接口
The runtime SHALL provide an `IStepExecutor` interface for executing individual plan steps.

- `execute_step(step, ctx, previous_results)` SHALL execute a single `ValidatedStep` and return a `StepResult`.
- `StepResult` MUST contain: `step_id`, `success`, `output`, `evidence`, `errors`.
- Implementations MAY invoke tools via `IToolGateway` based on step's `capability_id`.
- `StepResult.evidence` MUST be preserved into execute output so verify/remediation can consume it.

#### Scenario: Step executor invokes tool
- **GIVEN** a ValidatedStep with capability_id="write_file"
- **WHEN** `execute_step` is called
- **THEN** the executor invokes the tool via IToolGateway and returns a StepResult

#### Scenario: Step evidence is available for verification
- **WHEN** step execution produces evidence entries
- **THEN** execute loop output includes those entries for milestone verification

