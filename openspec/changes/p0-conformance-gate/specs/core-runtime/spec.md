## MODIFIED Requirements

### Requirement: Auditable Event Logging
The Kernel SHALL append structured events to `IEventLog` for state transitions, plan attempts, tool invocations, policy decisions, and verification outcomes, including correlation identifiers (task/session/milestone/run).

The emitted event schema MUST remain stable enough to support automated P0 conformance checks for security gating, step execution, and audit integrity.

#### Scenario: Tool invocation is logged
- **WHEN** `IToolGateway.invoke()` is called
- **THEN** an event is appended to `IEventLog` including capability id, derived risk, decision, and outcome

#### Scenario: Event schema supports conformance verification
- **WHEN** CI conformance tests query runtime events
- **THEN** required correlation and decision fields are present to validate P0 invariants

