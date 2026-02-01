"""OpenTelemetry-based telemetry provider implementation."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

try:
    from opentelemetry import metrics, trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    from opentelemetry.trace import Span as OTelSpan, SpanKind as OTelSpanKind, Status, StatusCode

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    except Exception:  # pragma: no cover - optional dependency
        OTLPSpanExporter = None

    try:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    except Exception:  # pragma: no cover - optional dependency
        OTLPMetricExporter = None

    try:
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
    except Exception:  # pragma: no cover - optional dependency
        ConsoleMetricExporter = None

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OTEL_AVAILABLE = False

from dare_framework.infra.component import ComponentType
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability.types import SpanStatus, TelemetryConfig


class GenAIAttributes:
    """OpenTelemetry GenAI semantic convention attribute names."""

    OPERATION_NAME = "gen_ai.operation.name"
    PROVIDER_NAME = "gen_ai.provider.name"
    REQUEST_MODEL = "gen_ai.request.model"

    INPUT_TOKENS = "gen_ai.usage.input_tokens"
    OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    TOTAL_TOKENS = "gen_ai.usage.total_tokens"

    AGENT_ID = "gen_ai.agent.id"
    AGENT_NAME = "gen_ai.agent.name"
    CONVERSATION_ID = "gen_ai.conversation.id"

    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call.id"

    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"


class DAREAttributes:
    """DARE Framework specific observability attributes."""

    CONTEXT_LENGTH = "dare.context.length"
    CONTEXT_MESSAGES_COUNT = "dare.context.messages_count"
    CONTEXT_TOOLS_COUNT = "dare.context.tools_count"

    SESSION_ID = "dare.session.id"
    RUN_ID = "dare.run.id"
    TASK_ID = "dare.task.id"
    MILESTONE_ID = "dare.milestone.id"
    MILESTONE_INDEX = "dare.milestone.index"
    MILESTONE_ATTEMPT = "dare.milestone.attempt"
    EXECUTE_ITERATION = "dare.execute.iteration"
    TOOL_ATTEMPT = "dare.tool.attempt"

    BUDGET_TOKENS_USED = "dare.budget.tokens.used"
    BUDGET_TOKENS_MAX = "dare.budget.tokens.max"
    BUDGET_COST_USED = "dare.budget.cost.used"
    BUDGET_TOOL_CALLS_USED = "dare.budget.tool_calls.used"

    EXECUTION_MODE = "dare.execution.mode"

    TOOL_RISK_LEVEL = "dare.tool.risk_level"
    TOOL_REQUIRES_APPROVAL = "dare.tool.requires_approval"
    TOOL_APPROVED = "dare.tool.approved"
    TOOL_EVIDENCE_COLLECTED = "dare.tool.evidence_collected"


class _SpanWrapper:
    def __init__(self, span: OTelSpan) -> None:
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        try:
            self._span.set_attribute(key, value)
        except Exception:
            return

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        try:
            self._span.add_event(name, attributes=attributes or {})
        except Exception:
            return

    def set_status(self, status: str, description: str | None = None) -> None:
        try:
            normalized = status.lower()
        except Exception:
            normalized = ""
        if normalized == SpanStatus.OK.value:
            code = StatusCode.OK
        elif normalized == SpanStatus.ERROR.value:
            code = StatusCode.ERROR
        else:
            code = StatusCode.UNSET
        try:
            self._span.set_status(Status(code, description=description))
        except Exception:
            return

    def end(self) -> None:
        try:
            self._span.end()
        except Exception:
            return


class OTelTelemetryProvider(ITelemetryProvider):
    """OpenTelemetry-based telemetry provider implementation."""

    def __init__(self, config: TelemetryConfig) -> None:
        self._config = config
        self._enabled = False
        self._tracer = None
        self._meter = None
        self._tracer_provider = None
        self._meter_provider = None
        self._token_usage_histogram = None
        self._operation_duration_histogram = None
        self._context_length_histogram = None
        self._tool_invocations_counter = None
        self._loop_iterations_counter = None

        if not OTEL_AVAILABLE or not config.enabled:
            return

        self._enabled = True
        self._tracer = self._setup_tracer()
        self._meter = self._setup_meter()
        self._setup_metrics()

    @property
    def name(self) -> str:
        return "otel"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    def _setup_tracer(self) -> Any:
        if not OTEL_AVAILABLE:
            return None

        resource = Resource.create(
            {
                "service.name": self._config.service_name,
                "service.version": self._config.service_version,
                "deployment.environment": self._config.deployment_environment,
                **self._config.resource_attributes,
            }
        )

        sampler = ParentBased(TraceIdRatioBased(self._config.sample_rate))
        provider = TracerProvider(resource=resource, sampler=sampler)

        if self._config.exporter_type == "console":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        elif self._config.exporter_type == "otlp" and OTLPSpanExporter is not None:
            exporter = OTLPSpanExporter(
                endpoint=self._config.otlp_endpoint or "http://localhost:4317",
                headers=self._config.otlp_headers or None,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        self._tracer_provider = provider
        return trace.get_tracer("dare-framework")

    def _setup_meter(self) -> Any:
        if not OTEL_AVAILABLE:
            return None

        readers = []
        if self._config.exporter_type == "console" and ConsoleMetricExporter is not None:
            readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
        elif self._config.exporter_type == "otlp" and OTLPMetricExporter is not None:
            readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(
                        endpoint=self._config.otlp_endpoint or "http://localhost:4317",
                        headers=self._config.otlp_headers or None,
                    )
                )
            )

        provider = MeterProvider(metric_readers=readers)
        metrics.set_meter_provider(provider)
        self._meter_provider = provider
        return metrics.get_meter("dare-framework")

    def _setup_metrics(self) -> None:
        if not self._meter:
            return

        self._token_usage_histogram = self._meter.create_histogram(
            name="gen_ai.client.token.usage",
            unit="{token}",
            description="Number of tokens used in GenAI operations",
        )
        self._operation_duration_histogram = self._meter.create_histogram(
            name="gen_ai.client.operation.duration",
            unit="s",
            description="Duration of GenAI operations",
        )
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
            yield _SpanWrapper(span)

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if not self._enabled or not self._meter:
            return

        attrs = attributes or {}

        if name == "gen_ai.client.token.usage" and self._token_usage_histogram is not None:
            self._token_usage_histogram.record(value, attrs)
        elif name == "gen_ai.client.operation.duration" and self._operation_duration_histogram is not None:
            self._operation_duration_histogram.record(value, attrs)
        elif name == "dare.context.length" and self._context_length_histogram is not None:
            self._context_length_histogram.record(value, attrs)
        elif name == "dare.tool.invocations" and self._tool_invocations_counter is not None:
            self._tool_invocations_counter.add(int(value), attrs)
        elif name == "dare.loop.iterations" and self._loop_iterations_counter is not None:
            self._loop_iterations_counter.add(int(value), attrs)

    def record_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if not self._enabled:
            return

        span = trace.get_current_span()
        if span and span.is_recording():
            span.add_event(name, attributes=attributes or {})

    def shutdown(self) -> None:
        if not self._enabled:
            return
        if self._tracer_provider is not None:
            try:
                self._tracer_provider.force_flush()
            except Exception:
                pass
            try:
                self._tracer_provider.shutdown()
            except Exception:
                pass
        if self._meter_provider is not None:
            try:
                self._meter_provider.shutdown()
            except Exception:
                pass


class NoOpTelemetryProvider(ITelemetryProvider):
    """No-op telemetry provider when OTel is disabled/unavailable."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

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
        return

    def record_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        return

    def shutdown(self) -> None:
        return


__all__ = [
    "OTelTelemetryProvider",
    "NoOpTelemetryProvider",
    "GenAIAttributes",
    "DAREAttributes",
    "OTEL_AVAILABLE",
]
