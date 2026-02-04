# Module: observability

> Status: v2 implementation (2026-02-01).

## 1. 定位与职责

- 提供基于 OpenTelemetry 的 traces / metrics / logs 观测能力（可选依赖）。
- 通过 Hook 与 EventLog 扩展点，做到最小侵入的采集与关联。
- 覆盖上下文长度、tokens 消耗、工具执行、调用链等核心指标。

## 2. 关键概念与数据结构

- `ITelemetryProvider`: 统一观测接口（start_span / record_metric / record_event）。
- `ISpan`: 最小 span 接口（set_attribute / add_event / set_status / end）。
- `TelemetryConfig`: OTel 相关配置（service / exporter / sampling / privacy）。
- `RunMetrics`: 单次运行聚合指标（tokens/context/tool/loops/budget）。
- `ObservabilityHook`: Hook 驱动的观测采集实现。
- `MetricsCollector`: RunMetrics 聚合器。
- `TraceAwareEventLog`: EventLog 注入 trace 上下文的桥接实现。

## 3. 关键接口与实现

- Kernel: `ITelemetryProvider`, `ISpan` (`dare_framework/observability/kernel.py`)
- Types: `TelemetryConfig`, `RunMetrics`, `SpanKind`, `SpanStatus` (`dare_framework/observability/types.py`)
- OpenTelemetry 实现:
  - `OTelTelemetryProvider` / `NoOpTelemetryProvider` (`dare_framework/observability/_internal/otel_provider.py`)
  - `ObservabilityHook` (`dare_framework/observability/_internal/tracing_hook.py`)
  - `MetricsCollector` (`dare_framework/observability/_internal/metrics_collector.py`)
  - `TraceAwareEventLog` (`dare_framework/observability/_internal/event_trace_bridge.py`)

## 4. 与其他模块的交互

- **Agent**
  - `DareAgent` 接收 `telemetry` 参数，默认使用 `NoOpTelemetryProvider`。
  - `DareAgent` 在初始化时包装 `event_log` 为 trace-aware。
  - 当 `telemetry` 为 `OTelTelemetryProvider` 时自动挂载 `ObservabilityHook`。
- **Hook**
  - `HookExtensionPoint` 分发 HookPhase payload。
  - `ObservabilityHook` 从 payload 提取关键字段，创建 spans/metrics。
- **EventLog**
  - `TraceAwareEventLog` 自动注入 `_trace` 字段并与 span 关联。

## 5. Hook payload 关键字段（v2）

最小要求字段（其余可扩展）：
- BEFORE_RUN: `task_id`, `session_id`, `agent_name`, `execution_mode`
- AFTER_RUN: `success`, `token_usage`, `errors`
- BEFORE_TOOL: `tool_name`, `tool_call_id`, `capability_id`, `attempt`, `risk_level`, `requires_approval`
- AFTER_TOOL: `tool_call_id`, `tool_name`, `success`, `error`, `approved`, `evidence_collected`

建议字段：
- AFTER_CONTEXT_ASSEMBLE: `context_length`, `context_messages_count`, `context_tools_count`
- AFTER_MODEL: `model_usage`（含 prompt/completion tokens）

## 6. Span 层级（v2）

```
dare.session
└── dare.milestone
    ├── dare.plan
    ├── dare.execute
    │   ├── llm.chat
    │   └── dare.tool
    └── dare.verify
```

## 7. Metrics（v2）

- `gen_ai.client.token.usage`（Histogram）
- `gen_ai.client.operation.duration`（Histogram）
- `dare.context.length`（Histogram）
- `dare.tool.invocations`（Counter）
- `dare.loop.iterations`（Counter）

## 8. 配置

`TelemetryConfig` 通过代码初始化：

```python
telemetry = OTelTelemetryProvider(
    TelemetryConfig(
        service_name="dare-framework",
        exporter_type="console",
        sample_rate=1.0,
    )
)
```

YAML 示例见 `doc/design/Observability_Design_v2.md`。

## 9. 现状与限制

- OpenTelemetry SDK 为可选依赖；缺失时自动退化为 no-op。
- 当前 Hook payload 仍以 Agent 层为主，工具内部细粒度 span 可后续补充。

## 10. Design Clarifications (2026-02-03)

- Doc gap: minimal hook payload schema must be treated as a contract across modules.
