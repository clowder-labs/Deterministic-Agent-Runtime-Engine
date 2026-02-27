## MODIFIED Requirements

### Requirement: TelemetryProvider extensibility via hooks and EventLog
The system SHALL expose observability extension points via `IExtensionPoint` hook emissions and `IEventLog` entries so TelemetryProvider components can emit traces, metrics, and logs.

When default event logging is enabled, EventLog-based telemetry correlation MUST continue to work without additional host wiring.

#### Scenario: Provider subscribes to runtime emissions
- **GIVEN** a TelemetryProvider is registered
- **WHEN** the runtime emits hook payloads or appends EventLog entries
- **THEN** the provider can generate corresponding telemetry with trace/span correlation

#### Scenario: Default event log entries carry telemetry correlation context
- **GIVEN** runtime uses default event log
- **WHEN** events are appended during a traced execution
- **THEN** the emitted event payload retains trace/span correlation fields consumable by telemetry bridges

