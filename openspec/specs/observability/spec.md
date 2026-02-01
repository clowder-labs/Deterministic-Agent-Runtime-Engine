# observability Specification

## Purpose
TBD - created by archiving change add-opentelemetry-observability. Update Purpose after archive.
## Requirements
### Requirement: OpenTelemetry emission for runtime telemetry
The system SHALL provide an optional OpenTelemetry-based observability subsystem that can emit traces, metrics, and logs for runtime operations.

#### Scenario: Telemetry is emitted when enabled
- **GIVEN** observability is enabled with a configured exporter
- **WHEN** an agent run executes
- **THEN** traces and metrics are emitted to the exporter

### Requirement: TelemetryProvider extensibility via hooks and EventLog
The system SHALL expose observability extension points via `IExtensionPoint` hook emissions and `IEventLog` entries so TelemetryProvider components can emit traces, metrics, and logs.

#### Scenario: Provider subscribes to runtime emissions
- **GIVEN** a TelemetryProvider is registered
- **WHEN** the runtime emits hook payloads or appends EventLog entries
- **THEN** the provider can generate corresponding telemetry with trace/span correlation

### Requirement: Trace-based call chain across runtime loops
The runtime SHALL create parent/child spans that represent the session, milestone, plan, execute, model, and tool stages, and SHALL propagate trace/span identifiers into EventLog payloads and hook emissions.

#### Scenario: Tool invocation is correlated to its parent span
- **WHEN** a tool is invoked during execution
- **THEN** the tool span is a child of the execute span and the EventLog entry includes `trace_id` and `span_id`

### Requirement: Context length telemetry
The runtime SHALL record assembled context size (message count and token estimate) as telemetry attributes and metrics.

#### Scenario: Context size is captured on assembly
- **WHEN** context is assembled for a model call
- **THEN** telemetry records message count and token estimate for that assembly

### Requirement: Token usage telemetry
The runtime SHALL record model input/output token usage using provider-reported values when available, and SHALL emit usage via OpenTelemetry GenAI semantic conventions or a compatible `dare.*` schema.

#### Scenario: Model usage metrics are emitted
- **GIVEN** a model response includes usage statistics
- **WHEN** the response is processed
- **THEN** input and output token usage metrics are emitted

### Requirement: Tool execution telemetry
The runtime SHALL emit tool invocation counts, durations, and error counts with capability identifiers and risk metadata.

#### Scenario: Tool duration is recorded
- **WHEN** a tool invocation completes
- **THEN** a duration metric is recorded and the invocation counter increments

### Requirement: Safe defaults for sensitive data
The observability subsystem SHALL redact sensitive content by default and expose configuration for sampling, exporter selection, and content capture.

#### Scenario: Content is excluded by default
- **GIVEN** `capture_content` is disabled
- **WHEN** telemetry is emitted
- **THEN** prompt content and tool arguments are excluded from spans and logs

