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
The runtime SHALL orchestrate the five-layer loop (Session, Milestone, Plan, Execute, Tool) as defined in `doc/design/Architecture_v4.0.md`, delegating to the v4.0 interfaces in `doc/design/Interfaces_v4.0.md` (planner/validator/remediator/tool gateway/security boundary).

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

#### Scenario: Invalid plan does not leak
- **WHEN** a plan attempt fails validation
- **THEN** the Milestone context excludes the invalid plan steps and only retains the reflection

### Requirement: HITL Gate Between Plan and Execute
The Kernel SHALL place the human approval gate between Plan and Execute, using `ISecurityBoundary.check_policy()` and `IExecutionControl.pause()/resume()` semantics as defined in `doc/design/Architecture_v4.0.md` / `doc/design/Interfaces_v4.0.md`.

#### Scenario: Plan requires approval
- **WHEN** `ISecurityBoundary.check_policy(action="execute_plan", ...)` returns `APPROVE_REQUIRED`
- **THEN** the Kernel pauses via `IExecutionControl.pause()` and resumes only after an explicit resume signal
