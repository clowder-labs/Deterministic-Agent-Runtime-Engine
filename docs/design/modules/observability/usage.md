# Observability Usage

## Enable via config

```yaml
observability:
  enabled: true
  traces_enabled: true
  metrics_enabled: true
  logs_enabled: false
  exporter: otlp  # otlp | console | none
  otlp_endpoint: "http://localhost:4317"
  headers: {}
  insecure: true
  sampling_ratio: 1.0
  capture_content: false
  redaction:
    mode: denylist
    keys: ["prompt", "content", "arguments"]
    replacement: "[REDACTED]"
```

When `observability.enabled` is true, `DareAgentBuilder` will create a default
OpenTelemetry provider automatically.

## Manual provider injection

```python
from dare_framework.agent import DareAgentBuilder
from dare_framework.config import Config
from dare_framework.observability.factory import create_default_telemetry_providers

config = Config()
providers = create_default_telemetry_providers(config, service_name="dare-agent-demo")

agent = (
    DareAgentBuilder("demo")
    .with_config(config)
    .add_telemetry_providers(*providers)
    .build()
)
```

## Notes
- OpenTelemetry SDK dependencies are optional. If the SDK is missing, the provider
  will no-op without failing the runtime.
- Content capture is disabled by default. Use `capture_content: true` only in
  trusted local environments.

## Local JSONL capture for examples

For local debugging you can capture every model input/output pair as JSONL:

```bash
export DARE_LLM_IO_CAPTURE=1
# optional: customize output directory (default: <workspace>/.dare/observability/llm_io)
export DARE_LLM_IO_DIR=".dare/observability/llm_io"
python examples/04-dare-coding-agent/main.py
```

When enabled, DareAgentBuilder auto-injects `llm_io_capture` hook and writes one
record per model call to a local JSONL file. The file key is:
- `<conversation_id>.llm_io.jsonl` when hook payload includes `conversation_id`
- `<run_id>.llm_io.jsonl` otherwise

Summarize the latest trace:

```bash
python scripts/llm_io_summary.py
```

Show per-call preview:

```bash
python scripts/llm_io_summary.py --show-calls
```
