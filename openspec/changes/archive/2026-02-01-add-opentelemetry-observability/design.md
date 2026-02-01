## Context
The runtime already exposes optional EventLog and Hook interfaces, but there is no unified observability layer. As a result, core questions (context length, token usage, tool counts, call chain) require manual inspection and are not exportable to standard telemetry backends.

This design introduces an OpenTelemetry (OTel) based observability capability that complements (not replaces) the WORM EventLog.

## Goals / Non-Goals
Goals:
- Provide tracing, metrics, and logs via OpenTelemetry with consistent correlation IDs.
- Capture context length, token consumption, tool execution counts, and call-chain structure.
- Keep sensitive content safe by default (redaction, opt-in content capture).
- Allow multiple exporters and sampling controls.

Non-Goals:
- Replacing the EventLog or changing its WORM/audit semantics.
- Forcing a specific vendor backend.
- Full cross-service distributed tracing across all external tools (out of scope for initial design).

## Design Overview
### High-level approach
- Add a new observability capability that emits OpenTelemetry traces, metrics, and logs.
- Observability is provided via pluggable TelemetryProvider components that consume runtime extension points (hooks and EventLog).
- Instrument runtime loops directly (session/milestone/plan/execute/tool/model/context) to emit hook payloads and EventLog entries.
- Correlate EventLog entries and hook payloads with trace/span identifiers.
- Use OTel GenAI semantic conventions for LLM-related spans/metrics when available; add `dare.*` attributes for DARE-specific needs.

### Rationale and references
- AgentScope provides built-in OpenTelemetry integration and tracing decorators, suggesting a light-weight opt-in setup.
- LangChain exposes a run tree via callback managers and tracing contexts, which maps well to parent/child spans.
- ADK provides end-to-end tracing of agent runs, tool calls, and model requests via OTel, validating the model/tool span hierarchy.

## Telemetry Model
### TelemetryProvider model (extensible)
- Define a TelemetryProvider interface (component) that translates runtime emissions into OTel traces/metrics/logs.
- Providers subscribe via `IExtensionPoint` (hooks) and/or `IEventLog` query/replay for batch/backfill.
- Multiple providers can be active (e.g., console + OTLP), sharing the same trace context.

### Trace/Span hierarchy (call chain)
Root span (per run) with nested spans:
- `dare.run` (root span)
  - `dare.session` (session loop)
    - `dare.milestone` (per milestone attempt)
      - `dare.plan` (plan attempt / validation)
      - `dare.execute` (execute loop iteration)
        - `dare.model` (model call)
        - `dare.tool` (tool invocation)

Each span includes:
- Core IDs: `dare.task_id`, `dare.run_id`, `dare.milestone_id`, `dare.plan_id` (when applicable)
- Correlation: `trace_id`, `span_id` (stored in EventLog payloads)
- Outcome: status, error summary

### Metrics
Required metrics (names are illustrative; final names align with OTel GenAI conventions where possible):
- Context length
  - Histogram of assembled context token count (and message count)
  - Dimensions: agent name, model, context_strategy
- Token usage
  - Counter or histogram for input/output token usage per model call
  - Dimensions: model name, provider, call type
- Tool execution
  - Counter for tool invocations
  - Histogram for tool duration
  - Counter for tool errors
  - Dimensions: capability_id, risk_level

### Logs
- Emit structured OTel logs for lifecycle events and errors.
- Do not log full prompt/tool arguments by default; allow opt-in content capture with redaction.
- Include trace/span identifiers for correlation in external log backends.

## Configuration
Add an `observability` configuration block with:
- `enabled`: bool
- `traces_enabled`, `metrics_enabled`, `logs_enabled`
- `exporter`: `otlp` | `console` | `none` (default `none` in local/dev)
- `otlp_endpoint`, `headers`, `insecure`
- `sampling_ratio`: float (0..1)
- `capture_content`: bool (default false)
- `redaction`: allow-list or deny-list rules for payload keys
- `attribute_cardinality_limits`: per-attribute caps

## Integration Points
### Hooks / ExtensionPoint
- Runtime emits structured hook payloads at lifecycle phases (before/after run/plan/tool/verify).
- TelemetryProviders attach to hooks to create spans/events/metrics in near real-time.

### EventLog
- Runtime appends WORM events with correlation IDs (`trace_id`, `span_id`).
- TelemetryProviders may consume EventLog for reconciliation, backfill, or offline analysis.

### Runtime loops
- Create spans at start/end of each loop stage via hook emissions.
- Add span events on transitions (`plan.validated`, `tool.invoke`, `tool.result`).
- Capture durations and link them to EventLog entries.

### Context assembly
- Record assembled context size (message count, token estimate).
- Store as metrics and as span attributes on the enclosing `dare.execute` span.

### Model adapter
- Record token usage from model response metadata when available.
- Set span attributes for model name, provider, and latency.

### Tool gateway
- Record tool invocation count/duration; include risk level and capability kind.
- Mark span status on tool errors and emit error logs.

### EventLog correlation
- Add `trace_id` and `span_id` into EventLog payloads without changing the WORM semantics.
- Use EventLog as authoritative audit; OTel is operational telemetry.

## Data Handling and Privacy
- Default to redacted content (no prompt/tool args in telemetry).
- Allow opt-in safe content capture for local debugging only.
- Ensure high-cardinality fields (raw prompts, file paths, user input) are excluded by default.

## Risks / Trade-offs
- Telemetry overhead if sampling is too high or content capture is enabled.
- High-cardinality attributes may overwhelm backends.
- Token estimation can be approximate; prefer provider-reported usage when available.

## Migration Plan
- Phase 1: Introduce observability config + OpenTelemetry emitter (no default exporter).
- Phase 2: Instrument runtime loops and model/tool paths.
- Phase 3: Add documentation, schema reference, and tests.

## Open Questions
- Should TelemetryProvider live in a new `observability` domain or be defined under `hook` as a component type?
- Which default exporter should be used for local development (console vs OTLP)?
- Do we require strict alignment with OTel GenAI semconv or allow project-specific names?
