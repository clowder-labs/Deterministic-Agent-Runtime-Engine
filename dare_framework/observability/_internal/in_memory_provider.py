"""In-memory telemetry provider for tests."""

from __future__ import annotations

from typing import Any, Literal

from dare_framework.config.types import ObservabilityConfig
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.observability._internal.context import pop_ids, push_ids
from dare_framework.observability._internal.redaction import redact_payload
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability.types import TelemetryMetricNames, TelemetrySpanNames


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


class InMemoryTelemetryProvider(ITelemetryProvider):
    """Telemetry provider that records spans and metrics in memory."""

    def __init__(self, config: ObservabilityConfig | None = None) -> None:
        self._config = config or ObservabilityConfig(enabled=True)
        self.hook_events: list[tuple[HookPhase, dict[str, Any]]] = []
        self.event_events: list[tuple[str, dict[str, Any]]] = []
        self.spans: list[dict[str, Any]] = []
        self.metrics: list[dict[str, Any]] = []
        self._span_stack: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "in-memory-telemetry"

    @property
    def component_type(self) -> Literal[ComponentType.TELEMETRY]:
        return ComponentType.TELEMETRY

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> None:
        payload = kwargs.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        payload = redact_payload(payload, self._config)
        self.hook_events.append((phase, payload))

        span_name = _PHASE_TO_SPAN.get(phase)
        if span_name is not None:
            if phase.name.startswith("BEFORE"):
                span = {
                    "name": span_name,
                    "attributes": dict(payload),
                    "parent": self._span_stack[-1]["name"] if self._span_stack else None,
                }
                self._span_stack.append(span)
                self.spans.append(span)
                trace_id = f"trace-{len(self.spans)}"
                span_id = f"span-{len(self.spans)}"
                push_ids(trace_id, span_id)
            else:
                if self._span_stack:
                    self._span_stack.pop()
                pop_ids()

        self._record_metrics(payload)

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.event_events.append((event_type, redact_payload(payload, self._config)))

    async def shutdown(self) -> None:
        return None

    def _record_metrics(self, payload: dict[str, Any]) -> None:
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
        if duration_ms is not None:
            phase = payload.get("phase")
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
        if value is None:
            return
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return
        self.metrics.append({"name": name, "value": numeric})


__all__ = ["InMemoryTelemetryProvider"]
