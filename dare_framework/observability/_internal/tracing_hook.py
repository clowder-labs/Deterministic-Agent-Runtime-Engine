"""Observability hook that instruments agent lifecycle with OpenTelemetry."""

from __future__ import annotations

import time
from typing import Any, Literal

from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.observability._internal.metrics_collector import MetricsCollector
from dare_framework.observability._internal.otel_provider import DAREAttributes, GenAIAttributes
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability.types import RunMetrics, SpanStatus


class ObservabilityHook(IHook):
    """Hook that instruments agent lifecycle with OpenTelemetry."""

    def __init__(self, telemetry: ITelemetryProvider) -> None:
        self._telemetry = telemetry
        self._active_spans: dict[str, tuple[Any, Any]] = {}
        self._timings: dict[str, float] = {}
        self._metrics_collector = MetricsCollector()
        self._current_metrics: RunMetrics | None = None

    @property
    def name(self) -> str:
        return "observability"

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> Any:
        payload = kwargs.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        if "budget_stats" in payload:
            self._metrics_collector.record_budget(payload.get("budget_stats"))
        if "error" in payload:
            self._metrics_collector.record_error(payload.get("error"))
        if "errors" in payload and isinstance(payload.get("errors"), list):
            for item in payload.get("errors", []):
                self._metrics_collector.record_error(item)
        try:
            if phase == HookPhase.BEFORE_RUN:
                await self._on_before_run(payload)
            elif phase == HookPhase.AFTER_RUN:
                await self._on_after_run(payload)
            elif phase == HookPhase.BEFORE_SESSION:
                await self._on_before_session(payload)
            elif phase == HookPhase.AFTER_SESSION:
                await self._on_after_session(payload)
            elif phase == HookPhase.BEFORE_MILESTONE:
                await self._on_before_milestone(payload)
            elif phase == HookPhase.AFTER_MILESTONE:
                await self._on_after_milestone(payload)
            elif phase == HookPhase.BEFORE_PLAN:
                await self._on_before_plan(payload)
            elif phase == HookPhase.AFTER_PLAN:
                await self._on_after_plan(payload)
            elif phase == HookPhase.BEFORE_EXECUTE:
                await self._on_before_execute(payload)
            elif phase == HookPhase.AFTER_EXECUTE:
                await self._on_after_execute(payload)
            elif phase == HookPhase.BEFORE_MODEL:
                await self._on_before_model(payload)
            elif phase == HookPhase.AFTER_MODEL:
                await self._on_after_model(payload)
            elif phase == HookPhase.AFTER_CONTEXT_ASSEMBLE:
                await self._on_after_context(payload)
            elif phase == HookPhase.BEFORE_TOOL:
                await self._on_before_tool(payload)
            elif phase == HookPhase.AFTER_TOOL:
                await self._on_after_tool(payload)
            elif phase == HookPhase.BEFORE_VERIFY:
                await self._on_before_verify(payload)
            elif phase == HookPhase.AFTER_VERIFY:
                await self._on_after_verify(payload)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Span helpers
    # ------------------------------------------------------------------

    def _start_span(self, key: str, name: str, *, kind: str, attributes: dict[str, Any]) -> None:
        ctx = self._telemetry.start_span(name, kind=kind, attributes=attributes)
        try:
            span = ctx.__enter__()
        except Exception:
            return
        self._active_spans[key] = (ctx, span)

    def _end_span(self, key: str, *, status: str | None = None, description: str | None = None) -> Any | None:
        entry = self._active_spans.pop(key, None)
        if entry is None:
            return None
        ctx, span = entry
        if span is not None and status is not None:
            try:
                span.set_status(status, description)
            except Exception:
                pass
        try:
            ctx.__exit__(None, None, None)
        except Exception:
            pass
        return span

    # ------------------------------------------------------------------
    # BEFORE_RUN / AFTER_RUN - Session level
    # ------------------------------------------------------------------

    async def _on_before_run(self, payload: dict[str, Any]) -> None:
        task_id = payload.get("task_id", "unknown")
        session_id = payload.get("session_id", "unknown")
        agent_name = payload.get("agent_name", "dare-agent")
        execution_mode = payload.get("execution_mode", "unknown")

        self._current_metrics = self._metrics_collector.reset()
        self._timings["run"] = time.time()

        self._start_span(
            "run",
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
        )

    async def _on_after_run(self, payload: dict[str, Any]) -> None:
        success = bool(payload.get("success", False))
        errors = payload.get("errors", [])
        token_usage = payload.get("token_usage") or {}

        if self._current_metrics is not None:
            if not token_usage:
                token_usage = {
                    "input_tokens": self._current_metrics.total_input_tokens,
                    "output_tokens": self._current_metrics.total_output_tokens,
                    "total_tokens": self._current_metrics.total_input_tokens
                    + self._current_metrics.total_output_tokens,
                }
            if errors:
                self._current_metrics.errors_total += len(errors)

        span = self._end_span("run", status=SpanStatus.OK.value if success else SpanStatus.ERROR.value)
        if span is not None:
            try:
                span.set_attribute("success", success)
                span.set_attribute(
                    GenAIAttributes.INPUT_TOKENS,
                    int(token_usage.get("input_tokens", 0)),
                )
                span.set_attribute(
                    GenAIAttributes.OUTPUT_TOKENS,
                    int(token_usage.get("output_tokens", 0)),
                )
            except Exception:
                pass

        duration = time.time() - self._timings.pop("run", time.time())
        self._metrics_collector.record_duration(total=duration)
        self._telemetry.record_metric(
            "gen_ai.client.operation.duration",
            duration,
            attributes={
                GenAIAttributes.OPERATION_NAME: "invoke_agent",
                "success": success,
            },
        )

        if self._current_metrics:
            self._export_metrics(self._current_metrics)
            self._current_metrics = None

    # ------------------------------------------------------------------
    # BEFORE_SESSION / AFTER_SESSION
    # ------------------------------------------------------------------

    async def _on_before_session(self, payload: dict[str, Any]) -> None:
        session_id = payload.get("run_id") or payload.get("session_id")
        task_id = payload.get("task_id")
        attributes: dict[str, Any] = {}
        if session_id:
            attributes[DAREAttributes.SESSION_ID] = session_id
            attributes[DAREAttributes.RUN_ID] = session_id
        if task_id:
            attributes[DAREAttributes.TASK_ID] = task_id
        self._start_span("session", "dare.session", kind="internal", attributes=attributes)

    async def _on_after_session(self, payload: dict[str, Any]) -> None:
        success = bool(payload.get("success", False))
        self._end_span("session", status=SpanStatus.OK.value if success else SpanStatus.ERROR.value)

    # ------------------------------------------------------------------
    # BEFORE_MILESTONE / AFTER_MILESTONE
    # ------------------------------------------------------------------

    async def _on_before_milestone(self, payload: dict[str, Any]) -> None:
        milestone_id = payload.get("milestone_id", "unknown")
        milestone_index = payload.get("milestone_index")
        attributes = {DAREAttributes.MILESTONE_ID: milestone_id}
        if milestone_index is not None:
            attributes[DAREAttributes.MILESTONE_INDEX] = milestone_index
        self._timings[f"milestone_{milestone_id}"] = time.time()
        self._start_span(f"milestone_{milestone_id}", "dare.milestone", kind="internal", attributes=attributes)

    async def _on_after_milestone(self, payload: dict[str, Any]) -> None:
        milestone_id = payload.get("milestone_id", "unknown")
        success = bool(payload.get("success", False))
        self._end_span(
            f"milestone_{milestone_id}",
            status=SpanStatus.OK.value if success else SpanStatus.ERROR.value,
        )
        attempts = payload.get("attempts")
        if attempts is not None:
            try:
                self._metrics_collector.metrics.milestone_attempts += int(attempts)
            except (TypeError, ValueError):
                self._metrics_collector.record_milestone_attempt(success)
            else:
                if success:
                    self._metrics_collector.metrics.milestone_success += 1
        else:
            self._metrics_collector.record_milestone_attempt(success)

    # ------------------------------------------------------------------
    # BEFORE_PLAN / AFTER_PLAN
    # ------------------------------------------------------------------

    async def _on_before_plan(self, payload: dict[str, Any]) -> None:
        milestone_id = payload.get("milestone_id", "unknown")
        attempt = payload.get("attempt", 1)

        self._timings["plan"] = time.time()
        self._start_span(
            "plan",
            "dare.plan",
            kind="internal",
            attributes={
                DAREAttributes.MILESTONE_ID: milestone_id,
                DAREAttributes.MILESTONE_ATTEMPT: attempt,
            },
        )

    async def _on_after_plan(self, payload: dict[str, Any]) -> None:
        valid = bool(payload.get("valid", payload.get("success", False)))
        self._end_span("plan", status=SpanStatus.OK.value if valid else SpanStatus.ERROR.value)
        self._metrics_collector.record_plan_attempt(valid)

    # ------------------------------------------------------------------
    # BEFORE_EXECUTE / AFTER_EXECUTE
    # ------------------------------------------------------------------

    async def _on_before_execute(self, payload: dict[str, Any]) -> None:
        self._timings["execute"] = time.time()
        self._start_span("execute", "dare.execute", kind="internal", attributes={})

    async def _on_after_execute(self, payload: dict[str, Any]) -> None:
        success = bool(payload.get("success", False))
        self._end_span("execute", status=SpanStatus.OK.value if success else SpanStatus.ERROR.value)

    # ------------------------------------------------------------------
    # BEFORE_MODEL / AFTER_MODEL
    # ------------------------------------------------------------------

    async def _on_before_model(self, payload: dict[str, Any]) -> None:
        model_name = payload.get("model_name")
        attributes = {GenAIAttributes.OPERATION_NAME: "chat"}
        iteration = payload.get("iteration")
        if iteration is not None:
            attributes[DAREAttributes.EXECUTE_ITERATION] = iteration
        if model_name:
            attributes[GenAIAttributes.REQUEST_MODEL] = model_name
        self._timings["model"] = time.time()
        self._metrics_collector.record_execute_iteration()
        self._metrics_collector.record_model_invocation()
        self._start_span("model", "llm.chat", kind="client", attributes=attributes)

    async def _on_after_model(self, payload: dict[str, Any]) -> None:
        usage = payload.get("model_usage")
        span = self._end_span("model", status=SpanStatus.OK.value)
        if span is not None and isinstance(usage, dict):
            try:
                input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)))
                output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)))
                total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens))
                span.set_attribute(GenAIAttributes.INPUT_TOKENS, input_tokens)
                span.set_attribute(GenAIAttributes.OUTPUT_TOKENS, output_tokens)
                span.set_attribute(GenAIAttributes.TOTAL_TOKENS, total_tokens)
            except Exception:
                pass

        duration = time.time() - self._timings.pop("model", time.time())
        self._metrics_collector.record_duration(model=duration)
        self._telemetry.record_metric(
            "gen_ai.client.operation.duration",
            duration,
            attributes={
                GenAIAttributes.OPERATION_NAME: "chat",
                "success": True,
            },
        )
        self._metrics_collector.record_model_usage(usage if isinstance(usage, dict) else None)

    # ------------------------------------------------------------------
    # AFTER_CONTEXT_ASSEMBLE
    # ------------------------------------------------------------------

    async def _on_after_context(self, payload: dict[str, Any]) -> None:
        length = payload.get("context_length")
        messages_count = payload.get("context_messages_count")
        tools_count = payload.get("context_tools_count", 0)
        if length is None or messages_count is None:
            return
        try:
            self._metrics_collector.record_context(
                int(length),
                int(messages_count),
                int(tools_count or 0),
            )
        except Exception:
            return

    # ------------------------------------------------------------------
    # BEFORE_TOOL / AFTER_TOOL
    # ------------------------------------------------------------------

    async def _on_before_tool(self, payload: dict[str, Any]) -> None:
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

        self._timings[f"tool_{tool_call_id}"] = time.time()
        self._start_span(f"tool_{tool_call_id}", "dare.tool", kind="client", attributes=attributes)

        self._telemetry.record_metric(
            "dare.tool.invocations",
            1,
            attributes={
                "tool_name": tool_name,
                "risk_level": risk_level,
            },
        )

    async def _on_after_tool(self, payload: dict[str, Any]) -> None:
        tool_call_id = payload.get("tool_call_id", "")
        tool_name = payload.get("tool_name", "unknown")
        success = bool(payload.get("success", False))
        error = payload.get("error")
        approved = payload.get("approved", True)
        policy_decision = payload.get("policy_decision")
        evidence_collected = payload.get("evidence_collected", False)

        span = self._end_span(
            f"tool_{tool_call_id}",
            status=SpanStatus.OK.value if success else SpanStatus.ERROR.value,
        )
        if span is not None:
            try:
                span.set_attribute("success", success)
                span.set_attribute(DAREAttributes.TOOL_APPROVED, approved)
                span.set_attribute(DAREAttributes.TOOL_EVIDENCE_COLLECTED, evidence_collected)
                if policy_decision is not None:
                    span.set_attribute("dare.tool.policy_decision", policy_decision)
                if error:
                    span.set_attribute(GenAIAttributes.ERROR_TYPE, type(error).__name__)
                    span.set_attribute(GenAIAttributes.ERROR_MESSAGE, str(error))
            except Exception:
                pass

        duration = time.time() - self._timings.pop(f"tool_{tool_call_id}", time.time())
        self._metrics_collector.record_duration(tool=duration)
        self._telemetry.record_metric(
            "gen_ai.client.operation.duration",
            duration,
            attributes={
                GenAIAttributes.OPERATION_NAME: "execute_tool",
                "tool_name": tool_name,
                "success": success,
            },
        )

        self._metrics_collector.record_tool_call(tool_name, success)

    # ------------------------------------------------------------------
    # BEFORE_VERIFY / AFTER_VERIFY
    # ------------------------------------------------------------------

    async def _on_before_verify(self, payload: dict[str, Any]) -> None:
        milestone_id = payload.get("milestone_id", "unknown")
        self._start_span(
            "verify",
            "dare.verify",
            kind="internal",
            attributes={DAREAttributes.MILESTONE_ID: milestone_id},
        )

    async def _on_after_verify(self, payload: dict[str, Any]) -> None:
        success = bool(payload.get("success", False))
        self._end_span("verify", status=SpanStatus.OK.value if success else SpanStatus.ERROR.value)

    # ------------------------------------------------------------------
    # Metrics export
    # ------------------------------------------------------------------

    def _export_metrics(self, metrics: RunMetrics) -> None:
        if not metrics:
            return

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
        self._telemetry.record_metric(
            "dare.context.length",
            metrics.max_context_length,
            attributes={"context_type": "max"},
        )
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
        total = float(metrics.total_duration)
        if total > 0:
            overhead = max(total - float(metrics.model_duration) - float(metrics.tool_duration), 0.0)
            ratio = overhead / total
        else:
            ratio = 0.0
        self._telemetry.record_metric(
            "hook.overhead_ratio",
            ratio,
            attributes={"phase": "run"},
        )


__all__ = ["ObservabilityHook"]
