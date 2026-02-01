# DARE Framework OpenTelemetry 可观测性设计 (v2)

> **设计原则**：基于 Opus 4.5 设计，严格遵循 DARE Framework 的 IHook/IExtensionPoint 和 IEventLog 理念

---

## 设计概述

### 核心理念

1. **可观测性是能力，不是侵入** - 通过 Hook 扩展点集成，不污染核心执行路径
2. **审计是权威，追踪是补充** - EventLog 依然是 7 年审计的权威源，OTel 作为运行时可观测性补充
3. **抽象优先，具体可选** - `ITelemetryProvider` 抽象允许替换实现，OpenTelemetry 是默认实现
4. **最佳努力，优雅降级** - Hooks 是 best-effort 的，可观测性失败不应影响主流程

### 架构层次

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DARE Framework Core                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────────┐   │
│  │  DareAgent   │  │  IEventLog   │  │  IExtensionPoint.emit()        │   │
│  │  (five_layer)│  │  (audit log) │  │  BEFORE_RUN → AFTER_RUN       │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┬────────────────┘   │
│         │                 │                     │                     │
│         │                 │                     ▼                     │
│         │                 │         ┌───────────────────────────────┐   │
│         │                 │         │  IHook.invoke(phase)          │   │
│         │                 │         │  BEFORE/AFTER_PLAN            │   │
│         │                 │         │  BEFORE/AFTER_TOOL            │   │
│         │                 │         └──────────────┬────────────────┘   │
│         │                 │                      │                     │
│         │                 │                      ▼                     │
│         │                 │         ┌───────────────────────────────┐   │
│         │                 │         │  ObservabilityHook            │   │
│         │                 │         │  (OTel + Metrics)             │   │
│         │                 │         └──────────────┬────────────────┘   │
│         │                 │                      │                     │
│         │                 │                      ▼                     │
│         │                 │         ┌───────────────────────────────┐   │
│         │                 │         │ ITelemetryProvider            │   │
│         │                 │         │ start_span()                  │   │
│         │                 │         │ record_metric()               │   │
│         │                 │         └──────────────┬────────────────┘   │
│         │                 │                      │                     │
└─────────┼─────────────────┼──────────────────────┼─────────────────────┘
          │                 │                      │
          │                 │                      ▼
          │                 │         ┌───────────────────────────────┐
          │                 │         │ OTelTelemetryProvider         │
          │                 │         │ (默认实现)                    │
          │                 │         └──────────────┬────────────────┘
          │                 │                      │
          │                 │                      ▼
          │                 │         ┌───────────────────────────────┐
          │                 │         │  OpenTelemetry SDK            │
          │                 │         │  Tracer + Meter               │
          │                 │         └──────────────┬────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    数据流向 (Two-Way)                                    │
│                                                                          │
│   EventLog ↔ OTel Traces/Metrics (互为补充，非替代)                      │
│   - EventLog: WORM 审计 (7 年留存，不可变)                               │
│   - OTel: 实时可观测性 (热数据，可查询)                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 组件：Observability Domain (NEW)

新建领域 `dare_framework/observability/`，遵循 DARE 的 domain-driven 架构。

```
dare_framework/observability/
├── __init__.py              # Domain facade
├── kernel.py                # [Kernel] ITelemetryProvider 接口
├── types.py                 # Type definitions
└── _internal/
    ├── otel_provider.py     # OpenTelemetry 实现
    ├── tracing_hook.py      # Hook 集成实现
    ├── metrics_collector.py # 指标聚合器
    └── event_trace_bridge.py # EventLog ↔ OTel 桥接
```

### 1.1 kernel.py - 核心接口

```python
"""Observability domain kernel interfaces."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Literal, Protocol, runtime_checkable

from dare_framework.infra.component import ComponentType, IComponent


@runtime_checkable
class ITelemetryProvider(Protocol):
    """[Kernel] Unified telemetry provider for traces, metrics, and logs.

    设计理念：
    1. 抽象优先：允许非 OTel 实现（如 Mock、自定义 exporter）
    2. 无侵入：方法设计为可选调用，返回 None 表示禁用
    3. 线程安全：实现需保证并发安全
    """

    @property
    def name(self) -> str:
        """Provider 名称（用于配置查找）"""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        kind: str = "internal",
        attributes: dict[str, Any] | None = None,
    ) -> Any:
        """Start a new span for tracing.

        Args:
            name: Span name (e.g., "dare.session", "dare.tool.invoke")
            kind: Span kind ("internal", "client", "server")
            attributes: Span attributes

        Returns:
            Context manager yielding span or None if disabled

        Note:
            返回 None 时调用方应正常执行，不中断流程
        """
        ...

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric value.

        Args:
            name: Metric name (e.g., "gen_ai.client.token.usage")
            value: Metric value
            attributes: Metric dimensions

        Note:
            最佳努力，失败时静默忽略
        """
        ...

    def record_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record an event on the current span.

        Args:
            name: Event name (e.g., "llm.prompt", "tool.error")
            attributes: Event attributes

        Note:
            无当前 span 时忽略
        """
        ...

    def shutdown(self) -> None:
        """Flush and shutdown the provider.

        Note:
            应用退出时调用，确保数据导出
        """
        ...


@runtime_checkable
class ISpan(Protocol):
    """[Kernel] Span interface for distributed tracing.

    注意：这是最小接口，OTel 实现可以提供更多方法。
    """

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        ...

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        ...

    def set_status(self, status: str, description: str | None = None) -> None:
        """Set span status ("ok", "error")."""
        ...

    def end(self) -> None:
        """End the span."""
        ...


__all__ = ["ITelemetryProvider", "ISpan"]
```

### 1.2 types.py - 类型定义

```python
"""Observability domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanKind(Enum):
    """Span kinds following OTel conventions."""

    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class GenAIOperation(Enum):
    """GenAI operation names per OTel semantic conventions."""

    CHAT = "chat"
    TEXT_COMPLETION = "text_completion"
    EMBEDDINGS = "embeddings"
    CREATE_AGENT = "create_agent"
    INVOKE_AGENT = "invoke_agent"
    EXECUTE_TOOL = "execute_tool"


class SpanStatus(Enum):
    """Span status values."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class TokenUsage:
    """Token usage tracking per OTel gen_ai.usage attributes."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class SpanContext:
    """Context for distributed tracing."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    trace_flags: int = 0


@dataclass
class TelemetryConfig:
    """Configuration for telemetry providers."""

    # Service identity
    service_name: str = "dare-framework"
    service_version: str = "1.0.0"
    deployment_environment: str = "production"

    # Enable/disable
    enabled: bool = True

    # Exporter configuration
    exporter_type: str = "console"  # console, otlp, none
    otlp_endpoint: str | None = None
    otlp_headers: dict[str, str] = field(default_factory=dict)

    # Sampling
    sample_rate: float = 1.0  # 1.0 = 全采样, 0.1 = 10%

    # Privacy
    capture_content: bool = False  # 是否捕获 prompts/responses（敏感）

    # Resource tags
    resource_attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class RunMetrics:
    """Aggregated metrics for a single agent run."""

    # Token tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cached_tokens: int = 0

    # Context tracking
    max_context_length: int = 0  # characters
    max_messages_count: int = 0
    max_tools_count: int = 0

    # Tool tracking
    tool_calls_total: int = 0
    tool_calls_success: int = 0
    tool_calls_failed: int = 0
    tool_by_name: dict[str, int] = field(default_factory=dict)

    # Loop tracking
    model_invocations: int = 0
    execute_iterations: int = 0
    milestone_attempts: int = 0
    milestone_success: int = 0
    plan_attempts: int = 0
    plan_success: int = 0

    # Timing (seconds)
    total_duration: float = 0.0
    model_duration: float = 0.0
    tool_duration: float = 0.0

    # Budget tracking
    budget_tokens_used: int = 0
    budget_tokens_limit: int | None = None
    budget_cost_used: float = 0.0

    # Error tracking
    errors_total: int = 0
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def record_tokens(self, input_tokens: int, output_tokens: int, cached: int = 0) -> None:
        """Record token usage from a model call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.cached_tokens += cached

    def record_context(self, length: int, messages_count: int, tools_count: int = 0) -> None:
        """Record context size."""
        self.max_context_length = max(self.max_context_length, length)
        self.max_messages_count = max(self.max_messages_count, messages_count)
        self.max_tools_count = max(self.max_tools_count, tools_count)

    def record_tool_call(self, tool_name: str, success: bool) -> None:
        """Record a tool invocation."""
        self.tool_calls_total += 1
        if success:
            self.tool_calls_success += 1
        else:
            self.tool_calls_failed += 1
        self.tool_by_name[tool_name] = self.tool_by_name.get(tool_name, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "tokens": {
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
                "total": self.total_input_tokens + self.total_output_tokens,
                "cached": self.cached_tokens,
            },
            "context": {
                "max_length": self.max_context_length,
                "max_messages": self.max_messages_count,
                "max_tools": self.max_tools_count,
            },
            "tools": {
                "total": self.tool_calls_total,
                "success": self.tool_calls_success,
                "failed": self.tool_calls_failed,
                "by_name": self.tool_by_name,
            },
            "loops": {
                "model_invocations": self.model_invocations,
                "execute_iterations": self.execute_iterations,
                "milestone_attempts": self.milestone_attempts,
                "milestone_success": self.milestone_success,
                "plan_attempts": self.plan_attempts,
                "plan_success": self.plan_success,
            },
            "timing": {
                "total_seconds": self.total_duration,
                "model_seconds": self.model_duration,
                "tool_seconds": self.tool_duration,
            },
            "budget": {
                "tokens_used": self.budget_tokens_used,
                "tokens_limit": self.budget_tokens_limit,
                "cost_used": self.budget_cost_used,
            },
            "errors": {
                "total": self.errors_total,
                "by_type": self.errors_by_type,
            },
        }


__all__ = [
    "SpanKind",
    "GenAIOperation",
    "SpanStatus",
    "TokenUsage",
    "SpanContext",
    "TelemetryConfig",
    "RunMetrics",
]
```

---

## 2. OpenTelemetry 实现

### 2.1 otel_provider.py - OTelTelemetryProvider

```python
"""OpenTelemetry-based telemetry provider implementation."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import Any, Generator

# OTel imports (optional)
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Span as OTelSpan, SpanKind as OTelSpanKind, Status, StatusCode
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability.types import (
    SpanKind,
    TelemetryConfig,
    SpanStatus,
)


# OpenTelemetry GenAI Semantic Convention Attributes
class GenAIAttributes:
    """OpenTelemetry GenAI semantic convention attribute names."""

    # Required attributes
    OPERATION_NAME = "gen_ai.operation.name"
    PROVIDER_NAME = "gen_ai.provider.name"
    REQUEST_MODEL = "gen_ai.request.model"

    # Token usage
    INPUT_TOKENS = "gen_ai.usage.input_tokens"
    OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    TOTAL_TOKENS = "gen_ai.usage.total_tokens"

    # Agent attributes
    AGENT_ID = "gen_ai.agent.id"
    AGENT_NAME = "gen_ai.agent.name"
    CONVERSATION_ID = "gen_ai.conversation.id"

    # Tool attributes
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call.id"

    # Error attributes
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"


# DARE-specific attributes (custom namespace)
class DAREAttributes:
    """DARE Framework specific observability attributes."""

    # Context tracking
    CONTEXT_LENGTH = "dare.context.length"
    CONTEXT_MESSAGES_COUNT = "dare.context.messages_count"
    CONTEXT_TOOLS_COUNT = "dare.context.tools_count"

    # Loop tracking
    SESSION_ID = "dare.session.id"
    RUN_ID = "dare.run.id"
    TASK_ID = "dare.task.id"
    MILESTONE_ID = "dare.milestone.id"
    MILESTONE_INDEX = "dare.milestone.index"
    MILESTONE_ATTEMPT = "dare.milestone.attempt"
    EXECUTE_ITERATION = "dare.execute.iteration"
    TOOL_ATTEMPT = "dare.tool.attempt"

    # Budget tracking
    BUDGET_TOKENS_USED = "dare.budget.tokens.used"
    BUDGET_TOKENS_MAX = "dare.budget.tokens.max"
    BUDGET_COST_USED = "dare.budget.cost.used"
    BUDGET_TOOL_CALLS_USED = "dare.budget.tool_calls.used"

    # Execution mode
    EXECUTION_MODE = "dare.execution.mode"  # full_five_layer, react, simple

    # Security tracking
    TOOL_RISK_LEVEL = "dare.tool.risk_level"
    TOOL_REQUIRES_APPROVAL = "dare.tool.requires_approval"
    TOOL_APPROVED = "dare.tool.approved"

    # Evidence tracking
    TOOL_EVIDENCE_COLLECTED = "dare.tool.evidence_collected"


class OTelTelemetryProvider(ITelemetryProvider):
    """OpenTelemetry-based telemetry provider implementation.

    优雅降级策略：
    1. OTel 不可用时返回 None，不报错
    2. 所有方法都是 best-effort，失败静默
    3. 禁用时通过 nullcontext 返回
    """

    def __init__(self, config: TelemetryConfig) -> None:
        if not OTEL_AVAILABLE or not config.enabled:
            self._enabled = False
            self._tracer = None
            self._meter = None
            return

        self._config = config
        self._enabled = True
        self._tracer = self._setup_tracer()
        self._meter = self._setup_meter()
        self._setup_metrics()

    @property
    def name(self) -> str:
        return "otel"

    @property
    def component_type(self) -> str:
        return "hook"

    def _setup_tracer(self) -> Any:
        """Setup OTel tracer."""
        if not OTEL_AVAILABLE:
            return None

        resource = Resource.create({
            "service.name": self._config.service_name,
            "service.version": self._config.service_version,
            "deployment.environment": self._config.deployment_environment,
            **self._config.resource_attributes,
        })

        provider = TracerProvider(resource=resource)

        # Add exporters
        if self._config.exporter_type == "console":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        elif self._config.exporter_type == "otlp" and self._config.otlp_endpoint:
            exporter = OTLPSpanExporter(
                endpoint=self._config.otlp_endpoint,
                headers=self._config.otlp_headers,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        return trace.get_tracer("dare-framework")

    def _setup_meter(self) -> Any:
        """Setup OTel meter."""
        if not OTEL_AVAILABLE:
            return None

        provider = MeterProvider(metric_readers=[
            PeriodicExportingMetricReader(
                ConsoleSpanExporter() if self._config.exporter_type == "console" else OTLPSpanExporter(
                    endpoint=self._config.otlp_endpoint or "http://localhost:4317",
                    headers=self._config.otlp_headers,
                ),
                export_interval_millis=15000,  # 15 秒导出一次
            )
        ])
        metrics.set_meter_provider(provider)
        return metrics.get_meter("dare-framework")

    def _setup_metrics(self) -> None:
        """Setup standard metrics."""
        if not self._meter:
            return

        # Token usage histogram (OTel standard)
        self._token_usage_histogram = self._meter.create_histogram(
            name="gen_ai.client.token.usage",
            unit="{token}",
            description="Number of tokens used in GenAI operations",
        )

        # Operation duration histogram (OTel standard)
        self._operation_duration_histogram = self._meter.create_histogram(
            name="gen_ai.client.operation.duration",
            unit="s",
            description="Duration of GenAI operations",
        )

        # DARE-specific metrics
        self._context_length_histogram = self._meter.create_histogram(
            name="dare.context.length",
            unit="{character}",
            description="Current context window length in characters",
        )

        self._tool_invocations_counter = self._meter.create_counter(
            name="dare.tool.invocations",
            unit="{call}",
            description="Number of tool invocations",
        )

        self._loop_iterations_counter = self._meter.create_counter(
            name="dare.loop.iterations",
            unit="{iteration}",
            description="Number of loop iterations",
        )

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        kind: str = "internal",
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Any, None, None]:
        """Start a new span for tracing."""
        if not self._enabled or not self._tracer:
            yield None
            return

        span_kind_map = {
            "internal": OTelSpanKind.INTERNAL,
            "client": OTelSpanKind.CLIENT,
            "server": OTelSpanKind.SERVER,
            "producer": OTelSpanKind.PRODUCER,
            "consumer": OTelSpanKind.CONSUMER,
        }
        span_kind = span_kind_map.get(kind, OTelSpanKind.INTERNAL)

        with self._tracer.start_as_current_span(
            name,
            kind=span_kind,
            attributes=attributes,
        ) as span:
            yield span

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric value."""
        if not self._enabled or not self._meter:
            return

        attrs = attributes or {}

        if name == "gen_ai.client.token.usage":
            self._token_usage_histogram.record(value, attrs)
        elif name == "gen_ai.client.operation.duration":
            self._operation_duration_histogram.record(value, attrs)
        elif name == "dare.context.length":
            self._context_length_histogram.record(value, attrs)
        elif name == "dare.tool.invocations":
            self._tool_invocations_counter.add(int(value), attrs)
        elif name == "dare.loop.iterations":
            self._loop_iterations_counter.add(int(value), attrs)

    def record_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record an event on the current span."""
        if not self._enabled:
            return

        span = trace.get_current_span()
        if span and span.is_recording():
            span.add_event(name, attributes=attributes or {})

    def shutdown(self) -> None:
        """Flush and shutdown the provider."""
        if self._enabled:
            # Flush span processors
            if self._tracer:
                tracer_provider = trace.get_tracer_provider()
                if tracer_provider:
                    # SDK shutdown handles flush
                    pass


# Null implementation for graceful degradation
class NoOpTelemetryProvider(ITelemetryProvider):
    """No-op telemetry provider when OTel is disabled/unavailable."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def component_type(self) -> str:
        return "hook"

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        kind: str = "internal",
        attributes: dict[str, Any] | None = None,
    ) -> Generator[None, None, None]:
        yield None

    def record_metric(self, name: str, value: float, *, attributes: dict[str, Any] | None = None) -> None:
        pass

    def record_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass

    def shutdown(self) -> None:
        pass


__all__ = [
    "OTelTelemetryProvider",
    "NoOpTelemetryProvider",
    "GenAIAttributes",
    "DAREAttributes",
    "OTEL_AVAILABLE",
]
```

---

## 3. Hook 集成实现

### 3.1 tracing_hook.py - ObservabilityHook

```python
"""Observability hook that uses IHook for OTel integration."""

from __future__ import annotations

import time
from typing import Any, Literal

from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability._internal.otel_provider import (
    GenAIAttributes,
    DAREAttributes,
)
from dare_framework.observability.types import RunMetrics


class ObservabilityHook(IHook):
    """Hook that instruments agent lifecycle with OpenTelemetry.

    设计原则：
    1. Best-effort：所有失败静默处理，不中断主流程
    2. Payload-driven：从 payload 提取关键信息，不假设数据结构
    3. Phase-agnostic：兼容现有的 HookPhase 枚举
    """

    def __init__(self, telemetry: ITelemetryProvider) -> None:
        self._telemetry = telemetry
        self._active_spans: dict[str, Any] = {}
        self._timings: dict[str, float] = {}
        self._current_metrics: RunMetrics | None = None

    @property
    def name(self) -> str:
        return "observability"

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> Any:
        """Invoke hook for lifecycle phase instrumentation.

        Phase mapping:
        - BEFORE_RUN → start session span
        - AFTER_RUN → end session span, export metrics
        - BEFORE_PLAN → start plan span
        - AFTER_PLAN → end plan span
        - BEFORE_TOOL → start tool span
        - AFTER_TOOL → end tool span
        - BEFORE_VERIFY → start verify span
        - AFTER_VERIFY → end verify span
        """
        try:
            if phase == HookPhase.BEFORE_RUN:
                await self._on_before_run(kwargs)
            elif phase == HookPhase.AFTER_RUN:
                await self._on_after_run(kwargs)
            elif phase == HookPhase.BEFORE_PLAN:
                await self._on_before_plan(kwargs)
            elif phase == HookPhase.AFTER_PLAN:
                await self._on_after_plan(kwargs)
            elif phase == HookPhase.BEFORE_TOOL:
                await self._on_before_tool(kwargs)
            elif phase == HookPhase.AFTER_TOOL:
                await self._on_after_tool(kwargs)
            elif phase == HookPhase.BEFORE_VERIFY:
                await self._on_before_verify(kwargs)
            elif phase == HookPhase.AFTER_VERIFY:
                await self._on_after_verify(kwargs)
        except Exception:
            # Best-effort: 所有异常静默处理
            pass

    # =========================================================================
    # BEFORE_RUN / AFTER_RUN - Session level
    # =========================================================================

    async def _on_before_run(self, payload: dict[str, Any]) -> None:
        """Start agent invocation span."""
        task_id = payload.get("task_id", "unknown")
        session_id = payload.get("session_id", "unknown")
        agent_name = payload.get("agent_name", "dare-agent")
        execution_mode = payload.get("execution_mode", "unknown")

        # Start metrics collection
        self._current_metrics = RunMetrics()
        self._timings["run"] = time.time()

        # Start session span
        with self._telemetry.start_span(
            "dare.session",
            kind="internal",
            attributes={
                GenAIAttributes.OPERATION_NAME: "invoke_agent",
                GenAIAttributes.AGENT_NAME: agent_name,
                DAREAttributes.TASK_ID: task_id,
                DAREAttributes.SESSION_ID: session_id,
                DAREAttributes.RUN_ID: session_id,
                DAREAttributes.EXECUTION_MODE: execution_mode,
            },
        ) as span:
            if span:
                self._active_spans["run"] = span

    async def _on_after_run(self, payload: dict[str, Any]) -> None:
        """End agent invocation span and export metrics."""
        span = self._active_spans.pop("run", None)
        if span:
            # Add final attributes
            success = payload.get("success", False)
            token_usage = payload.get("token_usage", {})
            errors = payload.get("errors", [])

            span.set_attribute("success", success)
            span.set_attribute(
                GenAIAttributes.INPUT_TOKENS,
                token_usage.get("input_tokens", 0),
            )
            span.set_attribute(
                GenAIAttributes.OUTPUT_TOKENS,
                token_usage.get("output_tokens", 0),
            )
            span.set_status("ok" if success else "error")

            # Record duration metric
            duration = time.time() - self._timings.pop("run", time.time())
            self._telemetry.record_metric(
                "gen_ai.client.operation.duration",
                duration,
                attributes={
                    GenAIAttributes.OPERATION_NAME: "invoke_agent",
                    "success": success,
                },
            )

        # Export aggregated metrics
        if self._current_metrics:
            self._export_metrics(self._current_metrics)
            self._current_metrics = None

    # =========================================================================
    # BEFORE_PLAN / AFTER_PLAN - Plan level
    # =========================================================================

    async def _on_before_plan(self, payload: dict[str, Any]) -> None:
        """Start plan generation span."""
        milestone_id = payload.get("milestone_id", "unknown")
        attempt = payload.get("attempt", 1)

        with self._telemetry.start_span(
            "dare.plan",
            kind="internal",
            attributes={
                DAREAttributes.MILESTONE_ID: milestone_id,
                DAREAttributes.MILESTONE_ATTEMPT: attempt,
            },
        ) as span:
            if span:
                self._active_spans["plan"] = span
                self._timings["plan"] = time.time()

    async def _on_after_plan(self, payload: dict[str, Any]) -> None:
        """End plan generation span."""
        span = self._active_spans.pop("plan", None)
        if span:
            valid = payload.get("valid", False)
            span.set_attribute("valid", valid)
            span.set_status("ok" if valid else "error")

            if self._current_metrics:
                self._current_metrics.plan_attempts += 1
                if valid:
                    self._current_metrics.plan_success += 1

    # =========================================================================
    # BEFORE_TOOL / AFTER_TOOL - Tool level
    # =========================================================================

    async def _on_before_tool(self, payload: dict[str, Any]) -> None:
        """Start tool execution span."""
        tool_name = payload.get("tool_name", "unknown")
        tool_call_id = payload.get("tool_call_id", "")
        capability_id = payload.get("capability_id", "")
        attempt = payload.get("attempt", 1)
        risk_level = payload.get("risk_level", 1)
        requires_approval = payload.get("requires_approval", False)

        attributes = {
            GenAIAttributes.OPERATION_NAME: "execute_tool",
            GenAIAttributes.TOOL_NAME: tool_name,
            GenAIAttributes.TOOL_CALL_ID: tool_call_id,
            DAREAttributes.TOOL_ATTEMPT: attempt,
            DAREAttributes.TOOL_RISK_LEVEL: risk_level,
            DAREAttributes.TOOL_REQUIRES_APPROVAL: requires_approval,
            "dare.tool.capability_id": capability_id,
        }

        with self._telemetry.start_span(
            "dare.tool",
            kind="client",
            attributes=attributes,
        ) as span:
            if span:
                self._active_spans[f"tool_{tool_call_id}"] = span
                self._timings[f"tool_{tool_call_id}"] = time.time()

        # Record tool invocation counter
        self._telemetry.record_metric(
            "dare.tool.invocations",
            1,
            attributes={
                "tool_name": tool_name,
                "risk_level": risk_level,
            },
        )

    async def _on_after_tool(self, payload: dict[str, Any]) -> None:
        """End tool execution span."""
        tool_call_id = payload.get("tool_call_id", "")
        tool_name = payload.get("tool_name", "unknown")

        span = self._active_spans.pop(f"tool_{tool_call_id}", None)
        if span:
            success = payload.get("success", False)
            error = payload.get("error")
            approved = payload.get("approved", True)
            evidence_collected = payload.get("evidence_collected", False)

            span.set_attribute("success", success)
            span.set_attribute(DAREAttributes.TOOL_APPROVED, approved)
            span.set_attribute(DAREAttributes.TOOL_EVIDENCE_COLLECTED, evidence_collected)

            if error:
                span.set_attribute(GenAIAttributes.ERROR_TYPE, type(error).__name__)
                span.set_attribute(GenAIAttributes.ERROR_MESSAGE, str(error))
                span.set_status("error")
            else:
                span.set_status("ok" if success else "error")

            # Record duration
            duration = time.time() - self._timings.pop(f"tool_{tool_call_id}", time.time())
            self._telemetry.record_metric(
                "gen_ai.client.operation.duration",
                duration,
                attributes={
                    GenAIAttributes.OPERATION_NAME: "execute_tool",
                    "tool_name": tool_name,
                    "success": success,
                },
            )

        # Update metrics
        if self._current_metrics:
            self._current_metrics.record_tool_call(tool_name, success)

    # =========================================================================
    # BEFORE_VERIFY / AFTER_VERIFY - Verification level
    # =========================================================================

    async def _on_before_verify(self, payload: dict[str, Any]) -> None:
        """Start verification span."""
        milestone_id = payload.get("milestone_id", "unknown")
        with self._telemetry.start_span(
            "dare.verify",
            kind="internal",
            attributes={
                DAREAttributes.MILESTONE_ID: milestone_id,
            },
        ) as span:
            if span:
                self._active_spans["verify"] = span

    async def _on_after_verify(self, payload: dict[str, Any]) -> None:
        """End verification span."""
        span = self._active_spans.pop("verify", None)
        if span:
            success = payload.get("success", False)
            span.set_attribute("success", success)
            span.set_status("ok" if success else "error")

            if self._current_metrics:
                if success:
                    self._current_metrics.milestone_success += 1

    # =========================================================================
    # Metrics export
    # =========================================================================

    def _export_metrics(self, metrics: RunMetrics) -> None:
        """Export aggregated metrics to telemetry provider."""
        if not metrics:
            return

        # Token usage
        self._telemetry.record_metric(
            "gen_ai.client.token.usage",
            metrics.total_input_tokens,
            attributes={"gen_ai.token.type": "input"},
        )
        self._telemetry.record_metric(
            "gen_ai.client.token.usage",
            metrics.total_output_tokens,
            attributes={"gen_ai.token.type": "output"},
        )

        # Context length
        self._telemetry.record_metric(
            "dare.context.length",
            metrics.max_context_length,
            attributes={"context_type": "max"},
        )

        # Loop iterations
        self._telemetry.record_metric(
            "dare.loop.iterations",
            metrics.execute_iterations,
            attributes={"loop_type": "execute"},
        )
        self._telemetry.record_metric(
            "dare.loop.iterations",
            metrics.model_invocations,
            attributes={"loop_type": "model"},
        )


__all__ = ["ObservabilityHook"]
```

---

## 4. EventLog ↔ OTel 桥接

### 4.1 event_trace_bridge.py

```python
"""Bridge between EventLog and OpenTelemetry traces.

设计理念：
1. EventLog 仍然是审计权威源（WORM，7 年留存）
2. OTel 提供 EventLog 的实时可查询能力
3. 双向关联：Event 记录 trace_id，Span 可以引用 event_id
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# OTel imports (optional)
try:
    from opentelemetry import trace
    from opentelemetry.trace import format_trace_id, format_span_id

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event


@dataclass
class TraceContext:
    """OpenTelemetry trace context."""

    trace_id: str
    span_id: str | None = None
    trace_flags: int = 0


def extract_trace_context() -> TraceContext | None:
    """Extract trace context from current OTel context.

    Returns:
        TraceContext if OTel is available and a span is active, else None
    """
    if not OTEL_AVAILABLE:
        return None

    ctx = trace.get_current_span().get_span_context()
    if not ctx.is_valid():
        return None

    return TraceContext(
        trace_id=format_trace_id(ctx.trace_id),
        span_id=format_span_id(ctx.span_id),
        trace_flags=ctx.trace_flags,
    )


class TraceAwareEventLog(IEventLog):
    """EventLog that automatically captures trace context.

    装饰器模式：包装现有的 IEventLog 实现，自动注入 trace 信息。
    """

    def __init__(self, inner_event_log: IEventLog) -> None:
        """Initialize with wrapped event log.

        Args:
            inner_event_log: The actual event log implementation
        """
        self._inner = inner_event_log

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        """Append event with automatic trace context injection.

        将 trace_id 和 span_id 注入到 Event 对象中，便于后续关联查询。
        """
        # 提取 trace context
        trace_ctx = extract_trace_context()

        # 构建 payload，添加 trace 信息
        enhanced_payload = dict(payload or {})
        if trace_ctx:
            enhanced_payload["_trace"] = {
                "trace_id": trace_ctx.trace_id,
                "span_id": trace_ctx.span_id,
                "trace_flags": trace_ctx.trace_flags,
            }

        # 调用内部 EventLog
        event_id = await self._inner.append(event_type, enhanced_payload)

        # 如果有 active span，添加 event 引用
        if trace_ctx and OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span and span.is_recording():
                span.add_event(
                    "event_log.append",
                    attributes={
                        "event.type": event_type,
                        "event.id": event_id,
                    },
                )

        return event_id

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Query events from inner event log."""
        return await self._inner.query(filter=filter, limit=limit)

    async def replay(self, *, from_event_id: str) -> Any:
        """Replay events from inner event log."""
        return await self._inner.replay(from_event_id=from_event_id)

    async def verify_chain(self) -> bool:
        """Verify chain from inner event log."""
        return await self._inner.verify_chain()


def make_trace_aware(event_log: IEventLog | None) -> IEventLog | None:
    """Make an event log trace-aware.

    Args:
        event_log: Event log instance or None

    Returns:
        TraceAwareEventLog wrapping the input, or None if input is None
    """
    if event_log is None:
        return None

    # 如果已经是 trace-aware，直接返回
    if isinstance(event_log, TraceAwareEventLog):
        return event_log

    return TraceAwareEventLog(event_log)


__all__ = [
    "TraceContext",
    "extract_trace_context",
    "TraceAwareEventLog",
    "make_trace_aware",
]
```

---

## 5. DareAgent 集成

### 5.1 修改点

在 `dare_framework/agent/_internal/five_layer.py` 中进行最小化集成：

```python
# 在 DareAgent.__init__ 中添加
from dare_framework.observability._internal.tracing_hook import ObservabilityHook
from dare_framework.observability._internal.event_trace_bridge import make_trace_aware
from dare_framework.observability._internal.otel_provider import (
    OTelTelemetryProvider,
    NoOpTelemetryProvider,
    TelemetryConfig,
)

class DareAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        *,
        # ... 现有参数 ...
        telemetry: ITelemetryProvider | None = None,  # 新增
        # ... 其他参数 ...
    ) -> None:
        # ... 现有初始化 ...

        # 初始化 telemetry（如果未提供）
        if telemetry is None:
            telemetry = NoOpTelemetryProvider()
        self._telemetry = telemetry

        # 包装 event_log 使其 trace-aware
        self._event_log = make_trace_aware(event_log)

        # 创建 observability hook 并添加到 hooks
        if isinstance(self._telemetry, OTelTelemetryProvider):
            self._observability_hook = ObservabilityHook(self._telemetry)
            if self._hooks is None:
                self._hooks = []
            self._hooks.append(self._observability_hook)
        else:
            self._observability_hook = None
```

### 5.2 Hook payload 数据结构

在各个 loop 中，需要确保 emit 的 payload 包含必需的字段：

```python
# BEFORE_RUN payload
{
    "task_id": task.id,
    "session_id": self._session_state.run_id,
    "agent_name": self.name,
    "execution_mode": "full_five_layer" | "react" | "simple",
}

# AFTER_RUN payload
{
    "success": True,
    "token_usage": {
        "input_tokens": total_input,
        "output_tokens": total_output,
    },
    "errors": [],
}

# BEFORE_TOOL payload
{
    "tool_name": tool_name,
    "tool_call_id": call_id,
    "capability_id": capability_id,
    "attempt": attempt,
    "risk_level": 1,  # 从 ToolManager 获取
    "requires_approval": True,  # 从 descriptor 获取
}

# AFTER_TOOL payload
{
    "tool_call_id": call_id,
    "tool_name": tool_name,
    "success": True,
    "error": None,
    "approved": True,
    "evidence_collected": True,
}
```

---

## 6. Span 层级设计

基于 DARE 五层架构的 span 层级：

```
dare.session [INTERNAL]
├── dare.session.start_event [EVENT]
├── dare.milestone [INTERNAL] (index=0)
│   ├── dare.plan [INTERNAL]
│   │   ├── llm.chat [CLIENT] (planner)
│   │   └── dare.plan.validation [INTERNAL]
│   ├── dare.execute [INTERNAL]
│   │   ├── llm.chat [CLIENT] (model)
│   │   │   └── gen_ai.content.prompt [EVENT]
│   │   │   └── gen_ai.content.completion [EVENT]
│   │   ├── dare.tool [CLIENT]
│   │   │   ├── dare.tool.invoke [CLIENT]
│   │   │   └── event_log.append [EVENT]
│   │   └── llm.chat [CLIENT] (model with tool results)
│   └── dare.verify [INTERNAL]
│       └── event_log.append [EVENT] (milestone.success)
├── dare.milestone [INTERNAL] (index=1)
│   └── ...
└── dare.session.end_event [EVENT]
    └── final_metrics_export
```

---

## 7. 属性约定

### 7.1 标准 GenAI 属性 (gen_ai.*)

| 属性 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `gen_ai.operation.name` | string | ✅ | 操作名称：invoke_agent, chat, execute_tool |
| `gen_ai.provider.name` | string | ✅ | 提供商：openai, anthropic |
| `gen_ai.request.model` | string | 条件 | 模型名称 |
| `gen_ai.usage.input_tokens` | int | 推荐 | 输入 tokens |
| `gen_ai.usage.output_tokens` | int | 推荐 | 输出 tokens |
| `gen_ai.usage.total_tokens` | int | 推荐 | 总 tokens |
| `gen_ai.agent.id` | string | 条件 | Agent ID |
| `gen_ai.agent.name` | string | 条件 | Agent 名称 |
| `gen_ai.conversation.id` | string | 条件 | 对话 ID |
| `gen_ai.tool.name` | string | 条件 | 工具名称 |
| `gen_ai.tool.call.id` | string | 条件 | 工具调用 ID |

### 7.2 DARE 专属属性 (dare.*)

| 属性 | 类型 | 描述 |
|------|------|------|
| `dare.session.id` | string | Session 唯一标识 |
| `dare.run.id` | string | Run 唯一标识 |
| `dare.task.id` | string | Task ID |
| `dare.milestone.id` | string | Milestone ID |
| `dare.milestone.index` | int | Milestone 在 session 中的索引 |
| `dare.milestone.attempt` | int | 当前尝试次数 |
| `dare.execute.iteration` | int | Execute 迭代次数 |
| `dare.tool.attempt` | int | Tool 调用尝试次数 |
| `dare.tool.risk_level` | int | 风险级别 (1-4) |
| `dare.tool.requires_approval` | bool | 是否需要审批 |
| `dare.tool.approved` | bool | 是否已审批 |
| `dare.tool.evidence_collected` | bool | 是否收集证据 |
| `dare.context.length` | int | 上下文长度（字符数） |
| `dare.context.messages_count` | int | 消息数量 |
| `dare.context.tools_count` | int | 工具数量 |
| `dare.budget.tokens.used` | int | 已用 tokens |
| `dare.budget.tokens.max` | int | tokens 限制 |
| `dare.budget.cost.used` | float | 已用成本 |
| `dare.budget.tool_calls.used` | int | 工具调用次数 |
| `dare.execution.mode` | string | 执行模式：full_five_layer, react, simple |

---

## 8. 指标设计

### 8.1 Counter 指标

| 名称 | 描述 | 单位 | 属性 |
|------|------|------|------|
| `dare.tool.invocations` | 工具调用次数 | {call} | tool_name, risk_level, success |
| `dare.loop.iterations` | 循环迭代次数 | {iteration} | loop_type (execute/model/plan) |

### 8.2 Histogram 指标

| 名称 | 描述 | 单位 | 推荐桶 |
|------|------|------|--------|
| `gen_ai.client.token.usage` | Tokens 消耗 | {token} | 100, 250, 500, 1k, 2k, 5k, 10k |
| `gen_ai.client.operation.duration` | 操作耗时 | s | 0.1, 0.5, 1, 2, 5, 10 |
| `dare.context.length` | 上下文长度 | {character} | 1k, 2k, 5k, 10k, 20k, 50k, 100k |

---

## 9. 配置示例

### 9.1 YAML 配置

```yaml
# config/telemetry.yaml
telemetry:
  enabled: true

  service:
    name: dare-framework
    version: "1.0.0"
    environment: production

  exporter:
    type: otlp  # console, otlp, none
    otlp:
      endpoint: "http://grafana:4317"
      headers:
        Authorization: "Bearer ${GRAFANA_TOKEN}"

  sampling:
    rate: 1.0  # 1.0 = 全采样

  privacy:
    capture_content: false  # 不捕获 prompts/responses

  resource:
    team: ml-ops
    deployment: production
```

### 9.2 Python 初始化

```python
from dare_framework.observability._internal.otel_provider import (
    OTelTelemetryProvider,
    TelemetryConfig,
)
from dare_framework.observability._internal.tracing_hook import ObservabilityHook

# 创建 telemetry provider
config = TelemetryConfig(
    service_name="dare-framework",
    service_version="1.0.0",
    deployment_environment="production",
    enabled=True,
    exporter_type="otlp",
    otlp_endpoint="http://grafana:4317",
    sample_rate=1.0,
    capture_content=False,
)

telemetry = OTelTelemetryProvider(config)

# 创建 observability hook
hook = ObservabilityHook(telemetry)

# 注入到 agent
agent = DareAgent(
    name="my-agent",
    model=model,
    telemetry=telemetry,
    hooks=[hook],
)
```

---

## 10. 实施阶段

### Phase 1: 基础设施（HIGH 优先级，1-2 周）

- [ ] 创建 `observability` domain 结构
- [ ] 实现 `ITelemetryProvider` 接口
- [ ] 实现 `OTelTelemetryProvider` 和 `NoOpTelemetryProvider`
- [ ] 实现 `ObservabilityHook`
- [ ] 添加可选依赖到 requirements.txt

### Phase 2: DareAgent 集成（HIGH 优先级，1-2 周）

- [ ] 在 DareAgent 中添加 telemetry 参数
- [ ] 在各 loop 中 emit hook payloads
- [ ] 实现 `make_trace_aware` 包装 EventLog
- [ ] 验证优雅降级（OTel 不可用时）

### Phase 3: 指标与验证（MEDIUM 优先级，1 周）

- [ ] 添加 MetricsCollector
- [ ] 定义并验证所有指标
- [ ] 编写单元测试
- [ ] 手动验证 Jaeger/Grafana 集成

### Phase 4: 高级特性（LOW 优先级，按需）

- [ ] 采样策略优化
- [ ] 批量导出配置
- [ ] 自定义 exporter
- [ ] Grafana dashboard 模板

---

## 11. 依赖

### requirements.txt

```ini
# OpenTelemetry (optional, for observability)
opentelemetry-api>=1.25.0
opentelemetry-sdk>=1.25.0
opentelemetry-exporter-otlp>=1.25.0
opentelemetry-semantic-conventions>=0.46b0
```

**注意**: OpenTelemetry 包是**可选依赖**。当未安装时，使用 `NoOpTelemetryProvider` 优雅降级。

---

## 12. 设计亮点

1. **完全兼容现有架构** - 使用 IHook 和 IEventLog，无需修改核心逻辑
2. **优雅降级** - OTel 不可用时自动使用 NoOp 实现，不影响主流程
3. **审计权威保留** - EventLog 仍然是 7 年审计的权威源
4. **双向关联** - Event 记录 trace_id，Span 可以引用 event_id
5. **最小侵入** - 通过 Hook 扩展点集成，核心代码零改动
6. **抽象优先** - ITelemetryProvider 允许替换实现
7. **合规考虑** - capture_content 默认 false，保护隐私

---

## 13. 与原始 Opus 设计对比

| 方面 | Opus 4.5 原版 | v2 优化版 |
|------|---------------|-----------|
| EventLog 集成 | ❌ 无 | ✅ TraceAwareEventLog 双向桥接 |
| 优雅降级 | ✅ 有 | ✅ 保留 + NoOpTelemetryProvider |
| IHook 集成 | ✅ 有 | ✅ 保留 + 更详细的 phase 映射 |
| 合规考虑 | ⚠️ 简单 | ✅ capture_content + 敏感字段 |
| 审计权威 | ⚠️ 未明确 | ✅ EventLog 仍是权威，OTel 补充 |
| Span 层级 | ⚠️ 简化 | ✅ 完整五层架构映射 |
| 错误处理 | ⚠️ 基础 | ✅ best-effort 静默失败 |
| 配置示例 | ⚠️ 简单 | ✅ 完整 YAML + Python |

---

**文档版本**: v2.0
**最后更新**: 2026-02-01
**状态**: 设计稿（待评审）
