# Change: Add OpenTelemetry-based runtime observability

## Why
The runtime currently has optional event logging and hook interfaces, but no unified observability design for tracing, metrics, or log correlation. This makes it hard to answer core runtime questions such as context length, token consumption, tool execution counts, and call chain analysis across the five-layer loops.

## What Changes
- Add a new observability capability spec that defines OpenTelemetry-based tracing, metrics, and log correlation for the runtime.
- Define telemetry schema (spans, attributes, metrics) for context length, token usage, tool activity, and call-chain structure.
- Specify configuration for exporters, sampling, and redaction to keep sensitive content safe by default.
- Define how TelemetryProvider components consume runtime hooks and EventLog entries, correlating OTel telemetry with the WORM audit log without replacing it.

## Impact
- Affected specs: new `observability` capability (future: possible touchpoints in `runtime-hooks` and `core-runtime`).
- Affected code (future): agent runtime loops, model adapter, tool gateway, context assembly, event log payloads, configuration surface.
- Risks: telemetry overhead, high-cardinality attributes, and privacy exposure if redaction is misconfigured.
