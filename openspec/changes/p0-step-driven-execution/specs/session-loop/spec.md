## MODIFIED Requirements

### Requirement: SessionContext initialization and config snapshot
The runtime SHALL create a SessionContext at the start of a session and bind the effective Config snapshot (if a ConfigProvider is supplied). The session start event SHALL include a `config_hash` derived from the snapshot.

The SessionContext MUST also record the effective `execution_mode` used for the run so downstream loops and audit events can determine whether execution is model-driven or step-driven.

#### Scenario: Session context includes config snapshot
- **GIVEN** a runtime configured with an `IConfigProvider`
- **WHEN** a session starts
- **THEN** SessionContext stores the effective Config snapshot
- **AND** `session.start` includes `config_hash`

#### Scenario: Session context includes execution mode
- **WHEN** a session starts with `execution_mode="step_driven"`
- **THEN** SessionContext records `execution_mode=step_driven`
- **AND** subsequent loop events can read the same mode value

