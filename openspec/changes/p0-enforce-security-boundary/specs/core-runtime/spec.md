## MODIFIED Requirements

### Requirement: ExecutionControl waiting interface
The system SHALL provide an explicit HITL waiting interface via `IExecutionControl.wait_for_human(checkpoint_id, reason)`.

This waiting interface MUST be used when security policy returns `APPROVE_REQUIRED` for plan execution or tool invocation.

#### Scenario: Approval-required plan execution
- **GIVEN** a validated plan that requires approval
- **WHEN** the orchestrator gates execution
- **THEN** it records `exec.pause`, calls `wait_for_human(...)`, and records `exec.resume` before continuing

#### Scenario: Approval-required tool invocation
- **GIVEN** a tool capability that requires approval
- **WHEN** policy evaluation returns `APPROVE_REQUIRED`
- **THEN** the orchestrator records `exec.pause`, calls `wait_for_human(...)`, and records `exec.resume` before continuing

### Requirement: Auditable Event Logging
The Kernel SHALL append structured events to `IEventLog` for state transitions, plan attempts, tool invocations, policy decisions, and verification outcomes, including correlation identifiers (task/session/milestone/run).

Security preflight events MUST include trust/policy outcomes before any tool side effects occur.

#### Scenario: Tool invocation is logged
- **WHEN** `IToolGateway.invoke()` is called
- **THEN** an event is appended to `IEventLog` including capability id, derived risk, decision, and outcome

#### Scenario: Policy denial is logged before invocation
- **WHEN** security policy denies a tool invocation
- **THEN** an event is appended with denial reason and correlation identifiers
- **AND** no invocation outcome event is emitted as success

