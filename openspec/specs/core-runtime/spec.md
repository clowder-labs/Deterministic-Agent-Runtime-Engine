# core-runtime Specification

## Purpose
TBD - created by archiving change add-runtime-config-model. Update Purpose after archive.
## Requirements
### Requirement: Session initialization applies effective config
The runtime SHALL resolve the effective configuration via ConfigProvider during session initialization and attach it to SessionContext before entering the Milestone Loop.

#### Scenario: Config available to runtime loops
- **WHEN** runtime.init() is called for a task
- **THEN** SessionContext carries the effective config snapshot so Plan/Execute/Tool loops and components can read consistent settings

### Requirement: ExecutionControl waiting interface
The system SHALL provide an explicit HITL waiting interface via `IExecutionControl.wait_for_human(checkpoint_id, reason)`.

#### Scenario: Approval-required plan execution
- **GIVEN** a validated plan that requires approval
- **WHEN** the orchestrator gates execution
- **THEN** it records `exec.pause`, calls `wait_for_human(...)`, and records `exec.resume` before continuing

#### Scenario: Approval-required tool invocation
- **GIVEN** a tool capability that requires approval
- **WHEN** the orchestrator attempts to invoke it
- **THEN** it records `exec.pause`, calls `wait_for_human(...)`, and records `exec.resume` before continuing

### Requirement: Five-Layer Runtime Orchestration
The runtime SHALL orchestrate the five-layer loop (Session, Milestone, Plan, Execute, Tool) as defined in `docs/design/Architecture.md`, delegating to the interfaces in `docs/design/Interfaces.md` (planner/validator/remediator/tool gateway/security boundary).

#### Scenario: Execute encounters a Plan Tool
- **WHEN** the Execute Loop encounters a tool classified as a Plan Tool
- **THEN** execution stops and control returns to the Milestone Loop to re-plan

#### Scenario: Tool Loop enforces DonePredicate
- **WHEN** a WorkUnit tool is invoked with an Envelope containing a DonePredicate
- **THEN** the Tool Loop retries until the DonePredicate is satisfied or budget is exhausted

### Requirement: Runtime State Machine
The runtime/orchestration SHALL expose init/run/pause/resume/stop/cancel (or equivalent) with auditable state transitions, and SHALL report the current RuntimeState.

#### Scenario: Pause and resume
- **WHEN** pause() is called while running
- **THEN** the runtime transitions to PAUSED and can later resume() to RUNNING

### Requirement: Auditable Event Logging
The Kernel SHALL append structured events to `IEventLog` for state transitions, plan attempts, tool invocations, policy decisions, and verification outcomes, including correlation identifiers (task/session/milestone/run).

#### Scenario: Tool invocation is logged
- **WHEN** `IToolGateway.invoke()` is called
- **THEN** an event is appended to `IEventLog` including capability id, derived risk, decision, and outcome

### Requirement: Checkpointing and Recovery
The runtime SHALL integrate ICheckpoint to persist state during pause/cancel paths and support resuming from a prior checkpoint.

#### Scenario: Pause creates a checkpoint
- **WHEN** pause() is invoked during an active session
- **THEN** a checkpoint is saved and is usable for resume()

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

### Requirement: HITL Gate Between Plan and Execute
The Kernel SHALL place the human approval gate between Plan and Execute, using `ISecurityBoundary.check_policy()` and `IExecutionControl.pause()/resume()` semantics as defined in `docs/design/Architecture.md` / `docs/design/Interfaces.md`.

#### Scenario: Plan requires approval
- **WHEN** `ISecurityBoundary.check_policy(action="execute_plan", ...)` returns `APPROVE_REQUIRED`
- **THEN** the Kernel pauses via `IExecutionControl.pause()` and resumes only after an explicit resume signal

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

