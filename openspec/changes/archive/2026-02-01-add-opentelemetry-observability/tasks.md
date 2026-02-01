## 1. Implementation
- [x] 1.1 Define TelemetryProvider interface + observability domain types (TelemetryContext, span/metric schemas)
- [x] 1.2 Add configuration surface for telemetry exporters, sampling, and redaction
- [x] 1.3 Implement OpenTelemetry emitter (traces, metrics, logs) with safe defaults
- [x] 1.4 Wire TelemetryProvider to IExtensionPoint (hooks) and IEventLog correlation
- [x] 1.5 Instrument agent loops (session/milestone/plan/execute/tool/model/context assemble)
- [x] 1.6 Add tests for span structure, metric emission, and redaction

## 2. Documentation
- [x] 2.1 Add usage guide for configuring exporters and viewing traces/metrics
- [x] 2.2 Add schema reference for emitted attributes and metrics
