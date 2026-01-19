## ADDED Requirements

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
