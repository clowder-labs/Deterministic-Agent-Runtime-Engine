## ADDED Requirements
### Requirement: Transport action channel exposes approval operations
The transport action path SHALL expose deterministic approval operations for runtime clients:
- `approvals:list`
- `approvals:grant`
- `approvals:deny`
- `approvals:revoke`

These operations SHALL be handled without entering the model prompt execution path.

#### Scenario: List pending approvals and rules
- **GIVEN** the runtime has at least one pending approval request
- **WHEN** the client sends action `approvals:list`
- **THEN** the response includes pending approvals and active approval rules

#### Scenario: Grant resolves pending approval
- **GIVEN** a pending approval request id exists
- **WHEN** the client sends action `approvals:grant` with that request id and a rule scope
- **THEN** the pending request is resolved as approved
- **AND** a corresponding rule is created according to the requested scope

#### Scenario: Deny resolves pending approval
- **GIVEN** a pending approval request id exists
- **WHEN** the client sends action `approvals:deny` with that request id
- **THEN** the pending request is resolved as denied

#### Scenario: Revoke removes persisted rule
- **GIVEN** an existing approval rule id
- **WHEN** the client sends action `approvals:revoke` with that rule id
- **THEN** the rule is removed from active approval memory
