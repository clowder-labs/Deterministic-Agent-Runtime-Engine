"""Observability domain data types and schema constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryContext:
    """Minimal telemetry context carried across runtime emissions."""

    agent_name: str
    task_id: str | None = None
    run_id: str | None = None
    milestone_id: str | None = None
    plan_attempt: int | None = None
    execute_iteration: int | None = None
    model_name: str | None = None


class TelemetrySpanNames:
    """Canonical span names for runtime tracing."""

    RUN = "dare.run"
    SESSION = "dare.session"
    MILESTONE = "dare.milestone"
    PLAN = "dare.plan"
    EXECUTE = "dare.execute"
    MODEL = "dare.model"
    TOOL = "dare.tool"
    CONTEXT = "dare.context"


class TelemetryMetricNames:
    """Canonical metric names for runtime observability."""

    CONTEXT_MESSAGES_COUNT = "context.messages.count"
    CONTEXT_TOKENS_ESTIMATE = "context.tokens.estimate"
    CONTEXT_LENGTH_CHARS = "context.length.chars"
    CONTEXT_LENGTH_BYTES = "context.length.bytes"
    CONTEXT_WINDOW_USED_RATIO = "context.window.used.ratio"

    MODEL_TOKENS_INPUT = "model.tokens.input"
    MODEL_TOKENS_OUTPUT = "model.tokens.output"
    MODEL_TOKENS_TOTAL = "model.tokens.total"
    MODEL_LATENCY_MS = "model.latency.ms"

    TOOL_CALLS_TOTAL = "tool.calls.total"
    TOOL_DURATION_MS = "tool.duration.ms"
    TOOL_ERRORS_TOTAL = "tool.errors.total"
    TOOL_RETRIES_TOTAL = "tool.retries.total"

    RUN_DURATION_MS = "run.duration.ms"
    SESSION_DURATION_MS = "session.duration.ms"
    MILESTONE_DURATION_MS = "milestone.duration.ms"
    PLAN_DURATION_MS = "plan.duration.ms"
    EXECUTE_DURATION_MS = "execute.duration.ms"

    BUDGET_TOKENS_USED = "budget.tokens.used"
    BUDGET_TOKENS_REMAINING = "budget.tokens.remaining"
    BUDGET_TOOL_CALLS_USED = "budget.tool_calls.used"
    BUDGET_TOOL_CALLS_REMAINING = "budget.tool_calls.remaining"
    BUDGET_TIME_USED_MS = "budget.time.used.ms"
    BUDGET_TIME_REMAINING_MS = "budget.time.remaining.ms"
    BUDGET_EXHAUSTED_COUNT = "budget.exhausted.count"


__all__ = [
    "TelemetryContext",
    "TelemetrySpanNames",
    "TelemetryMetricNames",
]
