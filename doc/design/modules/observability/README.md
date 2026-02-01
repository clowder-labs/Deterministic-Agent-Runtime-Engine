# Module: observability

> Status: initial implementation (2026-02-01). TODO marks follow-ups.

## 1. 定位与职责

- 提供基于 OpenTelemetry 的 traces / metrics / logs 观测能力。
- 通过 Hook + EventLog 扩展点输出 TelemetryProvider，可独立演进/替换。
- 以最小侵入方式采集上下文长度、token 消耗、工具执行、调用链等关键指标。

## 2. 关键概念与数据结构

- `ITelemetryProvider`: 观测组件接口（Hook 兼容 + EventLog 入口）。
- `TelemetrySpanNames`: 运行期 span 命名规范（`dare.run`, `dare.execute`, ...）。
- `TelemetryMetricNames`: 核心指标命名规范（context/tokens/tool/budget）。
- `TelemetryContext`: 运行期关联上下文（task/run/milestone/plan 等）。
- Redaction：默认去敏的 payload 处理策略。

## 3. 关键接口与实现

- Kernel: `ITelemetryProvider` (`dare_framework/observability/kernel.py`)
  - `invoke(phase, payload=...)` 作为 Hook 消费入口
  - `on_event(event_type, payload)` 消费 EventLog 入口
  - `shutdown()` flush/关闭
- Types: `TelemetrySpanNames`, `TelemetryMetricNames` (`dare_framework/observability/types.py`)
- Utilities: `estimate_tokens`, `summarize_messages` (`dare_framework/observability/utils.py`)
- Providers:
  - `OpenTelemetryProvider` (`dare_framework/observability/_internal/otel_provider.py`)
  - `InMemoryTelemetryProvider` (`dare_framework/observability/_internal/in_memory_provider.py`)
- Redaction:
  - `redact_payload` (`dare_framework/observability/_internal/redaction.py`)

## 4. 与其他模块的交互

- **Agent**
  - DareAgent 在 Run/Session/Milestone/Plan/Execute/Model/Tool/Context 关键点 emit hook。
  - EventLog 记录 `trace_id`/`span_id` 以便审计-观测关联。
- **Hook**
  - `HookExtensionPoint` 承担 Hook 分发，TelemetryProvider 通过 HookPhase 接收 payload。
- **EventLog**
  - `ITelemetryProvider.on_event(...)` 可订阅事件流（用于回放/补偿/离线分析）。
- **Config**
  - `observability` block 控制 exporter/sampling/redaction 与功能开关。

## 5. Payload / Schema 概览（与实现一致）

Hook payload 关键字段（均为可选）：
- `context_stats`: `messages_count`, `length_chars`, `length_bytes`, `tokens_estimate`
- `model_usage`: `prompt_tokens`, `completion_tokens`, `total_tokens`
- `tool_stats`: `success`, `duration_ms`
- `budget_stats`: `tokens_used`, `tokens_remaining`, `tool_calls_used`, `tool_calls_remaining`, `time_used_seconds`, `time_remaining_seconds`
- `duration_ms`: 运行阶段耗时
- `task_id`, `run_id`, `milestone_id`, `plan_attempt`, `iteration`

EventLog payload 会附加：
- `trace_id`, `span_id`（来自 TelemetryProvider 的上下文）

### 5.1 Span 对照表（实现映射）

| Span | HookPhase（start/end） | 触发位置 | 备注 |
| --- | --- | --- | --- |
| `dare.run` | `BEFORE_RUN` / `AFTER_RUN` | `dare_framework/agent/_internal/five_layer.py` | run 生命周期总跨度 |
| `dare.session` | `BEFORE_SESSION` / `AFTER_SESSION` | `dare_framework/agent/_internal/five_layer.py` | session loop |
| `dare.milestone` | `BEFORE_MILESTONE` / `AFTER_MILESTONE` | `dare_framework/agent/_internal/five_layer.py` | milestone loop |
| `dare.plan` | `BEFORE_PLAN` / `AFTER_PLAN` | `dare_framework/agent/_internal/five_layer.py` | plan attempt |
| `dare.execute` | `BEFORE_EXECUTE` / `AFTER_EXECUTE` | `dare_framework/agent/_internal/five_layer.py` | execute loop |
| `dare.context` | `BEFORE_CONTEXT_ASSEMBLE` / `AFTER_CONTEXT_ASSEMBLE` | `dare_framework/agent/_internal/five_layer.py` | assemble 过程 |
| `dare.model` | `BEFORE_MODEL` / `AFTER_MODEL` | `dare_framework/agent/_internal/five_layer.py` | model call |
| `dare.tool` | `BEFORE_TOOL` / `AFTER_TOOL` | `dare_framework/agent/_internal/five_layer.py` | tool invoke |

Span 映射由 TelemetryProvider 负责：
- `OpenTelemetryProvider` / `InMemoryTelemetryProvider` 使用 HookPhase → span name 规则（`dare_framework/observability/_internal/*_provider.py`）。

### 5.2 Metric 对照表（实现映射）

| Metric | 来源 payload | 触发位置 | 备注 |
| --- | --- | --- | --- |
| `context.messages.count` | `context_stats.messages_count` | `AFTER_CONTEXT_ASSEMBLE` | 组装消息数 |
| `context.tokens.estimate` | `context_stats.tokens_estimate` | `AFTER_CONTEXT_ASSEMBLE` | 估算 token |
| `context.length.chars` | `context_stats.length_chars` | `AFTER_CONTEXT_ASSEMBLE` | 字符长度 |
| `context.length.bytes` | `context_stats.length_bytes` | `AFTER_CONTEXT_ASSEMBLE` | 字节长度 |
| `model.tokens.input` | `model_usage.prompt_tokens` | `AFTER_MODEL` | 模型输入 |
| `model.tokens.output` | `model_usage.completion_tokens` | `AFTER_MODEL` | 模型输出 |
| `model.tokens.total` | `model_usage.total_tokens` | `AFTER_MODEL` | 模型总计 |
| `model.latency.ms` | `duration_ms` | `AFTER_MODEL` | 模型耗时 |
| `tool.calls.total` | `tool_stats` | `AFTER_TOOL` | 失败也计数 |
| `tool.duration.ms` | `tool_stats.duration_ms` | `AFTER_TOOL` | 工具耗时 |
| `tool.errors.total` | `tool_stats.success == False` | `AFTER_TOOL` | 失败计数 |
| `run.duration.ms` | `duration_ms` | `AFTER_RUN` | 总运行耗时 |
| `session.duration.ms` | `duration_ms` | `AFTER_SESSION` | session 耗时 |
| `milestone.duration.ms` | `duration_ms` | `AFTER_MILESTONE` | milestone 耗时 |
| `plan.duration.ms` | `duration_ms` | `AFTER_PLAN` | plan 尝试耗时 |
| `execute.duration.ms` | `duration_ms` | `AFTER_EXECUTE` | execute 耗时 |
| `budget.tokens.used` | `budget_stats.tokens_used` | `AFTER_*` | 运行期多处 |
| `budget.tokens.remaining` | `budget_stats.tokens_remaining` | `AFTER_*` | 运行期多处 |
| `budget.tool_calls.used` | `budget_stats.tool_calls_used` | `AFTER_*` | 运行期多处 |
| `budget.tool_calls.remaining` | `budget_stats.tool_calls_remaining` | `AFTER_*` | 运行期多处 |

## 6. 配置

`Config.observability` 对应 `ObservabilityConfig`：
- `enabled`, `traces_enabled`, `metrics_enabled`, `logs_enabled`
- `exporter`: `otlp` | `console` | `none`
- `otlp_endpoint`, `headers`, `insecure`
- `sampling_ratio`
- `capture_content`
- `redaction` (`mode`, `keys`, `replacement`)
- `attribute_cardinality_limits`

## 7. 现状与限制

- OpenTelemetry SDK 为可选依赖；缺失时 provider 退化为 no-op。
- 目前只在 Agent 层发出 hook payload；未对工具内部做深度 span。
- 当前 metrics 采用 histogram 记录，未区分 counter/histogram 类型。
- 运行结束的 flush 需要显式调用 `provider.shutdown()`（示例已覆盖）。

## 8. TODO / 未决问题

- TODO: 将 `logs_enabled` 接入 OpenTelemetry Logs SDK（当前使用标准 logging）。
- TODO: 更完整的 GenAI semantic conventions 映射（属性与 metric 命名）。
- TODO: 增加更细粒度的 tool/model 属性维度（需控制基数）。
- TODO: 默认 EventLog 回放/补偿策略与 OTEL span 对齐策略。
