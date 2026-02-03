## ADDED Requirements

### Requirement: Plan Attempt Sandbox 接口

The runtime SHALL provide an `IPlanAttemptSandbox` interface for state isolation during plan attempts.

- `create_snapshot(ctx)` SHALL save the current STM state and return a `snapshot_id`.
- `rollback(ctx, snapshot_id)` SHALL restore STM to the snapshot state, discarding subsequent changes.
- `commit(snapshot_id)` SHALL discard the snapshot, keeping the current state.
- Failed plan attempts MUST trigger rollback before the next attempt.

#### Scenario: Failed plan triggers rollback

- **GIVEN** a Milestone Loop with max_attempts=3
- **WHEN** the first plan attempt fails validation
- **THEN** STM is rolled back to the snapshot state before the next attempt

#### Scenario: Successful plan commits state

- **GIVEN** a plan that passes validation and execution
- **WHEN** `verify_milestone` returns success
- **THEN** the sandbox snapshot is committed (discarded) and state is preserved

---

### Requirement: Step-Driven Execution Mode

The runtime SHALL support a step-driven execution mode where the Execute Loop follows `ValidatedPlan.steps` sequentially.

- When `execution_mode="step_driven"`, the Execute Loop SHALL execute each `ValidatedStep` in order via `IStepExecutor`.
- Each step result SHALL be passed to the next step as context.
- If a step fails, execution SHALL halt and control returns to Milestone Loop for remediation.
- When `execution_mode="model_driven"` (default), the existing model-free execution behavior is preserved.

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

---

### Requirement: IStepExecutor 接口

The runtime SHALL provide an `IStepExecutor` interface for executing individual plan steps.

- `execute_step(step, ctx, previous_results)` SHALL execute a single `ValidatedStep` and return a `StepResult`.
- `StepResult` MUST contain: `step_id`, `success`, `output`, `evidence`, `errors`.
- Implementations MAY invoke tools via `IToolGateway` based on step's `capability_id`.

#### Scenario: Step executor invokes tool

- **GIVEN** a ValidatedStep with capability_id="write_file"
- **WHEN** `execute_step` is called
- **THEN** the executor invokes the tool via IToolGateway and returns a StepResult

---

## MODIFIED Requirements

### Requirement: Plan Attempt Isolation

Plan Loop attempts that fail validation SHALL NOT mutate Milestone context; only validated plans or reflections may be persisted to the outer loop state.

- **ENHANCED**: The runtime SHALL use `IPlanAttemptSandbox` to enforce state isolation.
- Snapshot is created at the start of each plan attempt.
- Failed attempts trigger rollback; successful attempts trigger commit.
- Reflection text from `IRemediator` is the only content preserved across failed attempts.

#### Scenario: Invalid plan does not leak

- **WHEN** a plan attempt fails validation
- **THEN** the Milestone context excludes the invalid plan steps and STM is rolled back to pre-attempt state

#### Scenario: Reflection preserved across attempts

- **GIVEN** a plan attempt that fails validation
- **WHEN** `IRemediator.remediate()` produces reflection text
- **THEN** the reflection is added to MilestoneState.reflections and survives the rollback
