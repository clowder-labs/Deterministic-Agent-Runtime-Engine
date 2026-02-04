# Observability Schema

## Span Names
- `dare.run`
- `dare.session`
- `dare.milestone`
- `dare.plan`
- `dare.execute`
- `dare.model`
- `dare.tool`
- `dare.context`

## Core Span Attributes
- `task_id`, `run_id`, `milestone_id`, `plan_attempt`, `execute_iteration`
- `model_name`, `capability_id`
- `duration_ms`, `success`, `errors`
- `trace_id`, `span_id` (also included in EventLog payloads)

## Metrics
| Metric | Meaning |
| --- | --- |
| `context.messages.count` | Assembled context message count |
| `context.tokens.estimate` | Estimated token count for context |
| `context.length.chars` | Context character length |
| `context.length.bytes` | Context byte length |
| `model.tokens.input` | Input tokens used |
| `model.tokens.output` | Output tokens used |
| `model.tokens.total` | Total tokens used |
| `model.latency.ms` | Model call latency |
| `tool.calls.total` | Tool invocation count |
| `tool.duration.ms` | Tool invocation duration |
| `tool.errors.total` | Tool error count |
| `run.duration.ms` | End-to-end run duration |
| `budget.tokens.used` | Token budget consumed |
| `budget.tokens.remaining` | Token budget remaining |
| `budget.tool_calls.used` | Tool call budget consumed |
| `budget.tool_calls.remaining` | Tool call budget remaining |

## Redaction
- By default, payload keys matching the redaction denylist are replaced with
  `[REDACTED]` before emission.
- Set `capture_content: true` to allow content payloads (still subject to explicit redaction keys).
