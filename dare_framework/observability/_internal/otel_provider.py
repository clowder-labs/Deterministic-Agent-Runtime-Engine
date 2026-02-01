"""OpenTelemetry telemetry provider implementation."""

from __future__ import annotations

import logging
from typing import Any, Literal

from dare_framework.config.types import ObservabilityConfig
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.observability._internal.context import pop_ids, push_ids
from dare_framework.observability._internal.redaction import redact_payload
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability.types import TelemetryMetricNames, TelemetrySpanNames

_logger = logging.getLogger("dare.telemetry")

_PHASE_TO_SPAN = {
    HookPhase.BEFORE_RUN: TelemetrySpanNames.RUN,
    HookPhase.AFTER_RUN: TelemetrySpanNames.RUN,
    HookPhase.BEFORE_SESSION: TelemetrySpanNames.SESSION,
    HookPhase.AFTER_SESSION: TelemetrySpanNames.SESSION,
    HookPhase.BEFORE_MILESTONE: TelemetrySpanNames.MILESTONE,
    HookPhase.AFTER_MILESTONE: TelemetrySpanNames.MILESTONE,
    HookPhase.BEFORE_PLAN: TelemetrySpanNames.PLAN,
    HookPhase.AFTER_PLAN: TelemetrySpanNames.PLAN,
    HookPhase.BEFORE_EXECUTE: TelemetrySpanNames.EXECUTE,
    HookPhase.AFTER_EXECUTE: TelemetrySpanNames.EXECUTE,
    HookPhase.BEFORE_MODEL: TelemetrySpanNames.MODEL,
    HookPhase.AFTER_MODEL: TelemetrySpanNames.MODEL,
    HookPhase.BEFORE_TOOL: TelemetrySpanNames.TOOL,
    HookPhase.AFTER_TOOL: TelemetrySpanNames.TOOL,
    HookPhase.BEFORE_CONTEXT_ASSEMBLE: TelemetrySpanNames.CONTEXT,
    HookPhase.AFTER_CONTEXT_ASSEMBLE: TelemetrySpanNames.CONTEXT,
}


class OpenTelemetryProvider(ITelemetryProvider):
    """Telemetry provider backed by OpenTelemetry SDK (optional dependency)."""

    def __init__(self, config: ObservabilityConfig, *, service_name: str = "dare-runtime") -> None:
        self._config = config
        self._service_name = service_name
        self._span_stack: list[Any] = []
        self._metrics: dict[str, Any] = {}
        self._available = False
        self._tracer = None
        self._meter = None
        self._log_emitter = None
        self._trace_provider = None
        self._meter_provider = None

        if not config.enabled:
            return

        try:
            from opentelemetry import metrics, trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        except Exception:
            _logger.warning("OpenTelemetry SDK not available; telemetry disabled")
            return

        resource = Resource.create({"service.name": service_name})

        if config.traces_enabled:
            sampler = ParentBased(TraceIdRatioBased(self._config.sampling_ratio))
            provider = TracerProvider(resource=resource, sampler=sampler)
            exporter = None
            if config.exporter == "console":
                exporter = ConsoleSpanExporter()
            elif config.exporter == "otlp":
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                        OTLPSpanExporter,
                    )

                    exporter = OTLPSpanExporter(
                        endpoint=config.otlp_endpoint,
                        headers=config.headers or None,
                        insecure=config.insecure,
                    )
                except Exception:
                    exporter = None
            if exporter is not None:
                provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self._trace_provider = provider
            self._tracer = trace.get_tracer("dare.observability")

        if config.metrics_enabled:
            if config.exporter == "console":
                metric_exporter = None
                try:
                    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

                    metric_exporter = ConsoleMetricExporter()
                except Exception:
                    metric_exporter = None
            elif config.exporter == "otlp":
                metric_exporter = None
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                        OTLPMetricExporter,
                    )

                    metric_exporter = OTLPMetricExporter(
                        endpoint=config.otlp_endpoint,
                        headers=config.headers or None,
                        insecure=config.insecure,
                    )
                except Exception:
                    metric_exporter = None
            else:
                metric_exporter = None

            readers = []
            if metric_exporter is not None:
                readers.append(PeriodicExportingMetricReader(metric_exporter))

            meter_provider = MeterProvider(resource=resource, metric_readers=readers)
            metrics.set_meter_provider(meter_provider)
            self._meter_provider = meter_provider
            self._meter = metrics.get_meter("dare.observability")

        self._available = self._tracer is not None or self._meter is not None or self._config.logs_enabled

    @property
    def name(self) -> str:
        return "opentelemetry"

    @property
    def component_type(self) -> Literal[ComponentType.TELEMETRY]:
        return ComponentType.TELEMETRY

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> None:
        if not self._available:
            return None
        payload = kwargs.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        payload = redact_payload(payload, self._config)

        span_name = _PHASE_TO_SPAN.get(phase)
        if span_name and self._tracer is not None:
            if phase.name.startswith("BEFORE"):
                parent_ctx = None
                if self._span_stack:
                    try:
                        from opentelemetry import trace

                        parent_ctx = trace.set_span_in_context(self._span_stack[-1])
                    except Exception:
                        parent_ctx = None
                span = self._tracer.start_span(span_name, context=parent_ctx)
                self._span_stack.append(span)
                self._apply_span_attributes(span, payload)
                self._push_ids(span)
            else:
                if self._span_stack:
                    span = self._span_stack.pop()
                    span.end()
                pop_ids()

        self._record_metrics(payload)

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self._available or not self._config.logs_enabled:
            return None
        payload = redact_payload(payload, self._config)
        _logger.info("telemetry event %s", event_type, extra={"payload": payload})

    async def shutdown(self) -> None:
        if self._trace_provider is not None:
            try:
                self._trace_provider.force_flush()
            except Exception:
                pass
            try:
                self._trace_provider.shutdown()
            except Exception:
                pass
        if self._meter_provider is not None:
            try:
                self._meter_provider.shutdown()
            except Exception:
                pass
        return None

    def _apply_span_attributes(self, span: Any, payload: dict[str, Any]) -> None:
        if not hasattr(span, "set_attribute"):
            return
        limits = self._config.attribute_cardinality_limits
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                continue
            if isinstance(value, str) and key in limits:
                value = value[: limits[key]]
            try:
                span.set_attribute(key, value)
            except Exception:
                continue

    def _record_metrics(self, payload: dict[str, Any]) -> None:
        if self._meter is None or not self._config.metrics_enabled:
            return
        context_stats = payload.get("context_stats")
        if isinstance(context_stats, dict):
            self._emit_metric(TelemetryMetricNames.CONTEXT_MESSAGES_COUNT, context_stats.get("messages_count"))
            self._emit_metric(TelemetryMetricNames.CONTEXT_TOKENS_ESTIMATE, context_stats.get("tokens_estimate"))
            self._emit_metric(TelemetryMetricNames.CONTEXT_LENGTH_CHARS, context_stats.get("length_chars"))
            self._emit_metric(TelemetryMetricNames.CONTEXT_LENGTH_BYTES, context_stats.get("length_bytes"))

        model_usage = payload.get("model_usage")
        if isinstance(model_usage, dict):
            self._emit_metric(TelemetryMetricNames.MODEL_TOKENS_INPUT, model_usage.get("prompt_tokens"))
            self._emit_metric(TelemetryMetricNames.MODEL_TOKENS_OUTPUT, model_usage.get("completion_tokens"))
            self._emit_metric(TelemetryMetricNames.MODEL_TOKENS_TOTAL, model_usage.get("total_tokens"))

        tool_stats = payload.get("tool_stats")
        if isinstance(tool_stats, dict):
            self._emit_metric(TelemetryMetricNames.TOOL_CALLS_TOTAL, 1)
            if "duration_ms" in tool_stats:
                self._emit_metric(TelemetryMetricNames.TOOL_DURATION_MS, tool_stats.get("duration_ms"))
            if tool_stats.get("success") is False:
                self._emit_metric(TelemetryMetricNames.TOOL_ERRORS_TOTAL, 1)

        budget_stats = payload.get("budget_stats")
        if isinstance(budget_stats, dict):
            self._emit_metric(TelemetryMetricNames.BUDGET_TOKENS_USED, budget_stats.get("tokens_used"))
            self._emit_metric(TelemetryMetricNames.BUDGET_TOKENS_REMAINING, budget_stats.get("tokens_remaining"))
            self._emit_metric(TelemetryMetricNames.BUDGET_TOOL_CALLS_USED, budget_stats.get("tool_calls_used"))
            self._emit_metric(
                TelemetryMetricNames.BUDGET_TOOL_CALLS_REMAINING,
                budget_stats.get("tool_calls_remaining"),
            )

        duration_ms = payload.get("duration_ms")
        phase = payload.get("phase")
        if duration_ms is not None and isinstance(phase, str):
            if phase == HookPhase.AFTER_RUN.value:
                self._emit_metric(TelemetryMetricNames.RUN_DURATION_MS, duration_ms)
            if phase == HookPhase.AFTER_SESSION.value:
                self._emit_metric(TelemetryMetricNames.SESSION_DURATION_MS, duration_ms)
            if phase == HookPhase.AFTER_MILESTONE.value:
                self._emit_metric(TelemetryMetricNames.MILESTONE_DURATION_MS, duration_ms)
            if phase == HookPhase.AFTER_PLAN.value:
                self._emit_metric(TelemetryMetricNames.PLAN_DURATION_MS, duration_ms)
            if phase == HookPhase.AFTER_EXECUTE.value:
                self._emit_metric(TelemetryMetricNames.EXECUTE_DURATION_MS, duration_ms)
            if phase == HookPhase.AFTER_MODEL.value:
                self._emit_metric(TelemetryMetricNames.MODEL_LATENCY_MS, duration_ms)

    def _emit_metric(self, name: str, value: Any) -> None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return
        instrument = self._metrics.get(name)
        if instrument is None:
            try:
                instrument = self._meter.create_histogram(name)
            except Exception:
                instrument = None
            if instrument is None:
                return
            self._metrics[name] = instrument
        try:
            instrument.record(numeric)
        except Exception:
            return

    def _push_ids(self, span: Any) -> None:
        try:
            span_context = span.get_span_context()
            trace_id = f"{span_context.trace_id:032x}"
            span_id = f"{span_context.span_id:016x}"
            push_ids(trace_id, span_id)
        except Exception:
            return


__all__ = ["OpenTelemetryProvider"]
