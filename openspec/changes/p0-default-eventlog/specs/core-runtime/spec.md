## MODIFIED Requirements

### Requirement: Auditable Event Logging
The Kernel SHALL append structured events to `IEventLog` for state transitions, plan attempts, tool invocations, policy decisions, and verification outcomes, including correlation identifiers (task/session/milestone/run).

Runtime builders SHOULD provide a default `IEventLog` implementation so auditable event logging is available by default rather than only via explicit injection.

#### Scenario: Tool invocation is logged
- **WHEN** `IToolGateway.invoke()` is called
- **THEN** an event is appended to `IEventLog` including capability id, derived risk, decision, and outcome

#### Scenario: Default runtime emits events without explicit event log injection
- **GIVEN** an agent is built without calling `with_event_log(...)`
- **WHEN** a session runs with default event logging enabled
- **THEN** core runtime events are persisted through the default event log implementation

