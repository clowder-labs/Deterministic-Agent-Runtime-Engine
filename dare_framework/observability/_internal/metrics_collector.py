"""Metrics aggregation helpers for observability hooks."""

from __future__ import annotations

from typing import Any

from dare_framework.observability.types import RunMetrics


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class MetricsCollector:
    """Aggregate per-run metrics from hook payloads."""

    def __init__(self) -> None:
        self._metrics = RunMetrics()

    @property
    def metrics(self) -> RunMetrics:
        return self._metrics

    def reset(self) -> RunMetrics:
        self._metrics = RunMetrics()
        return self._metrics

    def record_context(self, length: int, messages_count: int, tools_count: int = 0) -> None:
        self._metrics.record_context(length, messages_count, tools_count)

    def record_tool_call(self, tool_name: str, success: bool) -> None:
        self._metrics.record_tool_call(tool_name, success)

    def record_model_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        input_tokens = _coerce_int(usage.get("input_tokens", usage.get("prompt_tokens", 0)))
        output_tokens = _coerce_int(usage.get("output_tokens", usage.get("completion_tokens", 0)))
        cached_tokens = _coerce_int(usage.get("cached_tokens", 0))
        self._metrics.record_tokens(input_tokens, output_tokens, cached_tokens)

    def record_execute_iteration(self) -> None:
        self._metrics.execute_iterations += 1

    def record_model_invocation(self) -> None:
        self._metrics.model_invocations += 1

    def record_plan_attempt(self, success: bool) -> None:
        self._metrics.plan_attempts += 1
        if success:
            self._metrics.plan_success += 1

    def record_milestone_attempt(self, success: bool) -> None:
        self._metrics.milestone_attempts += 1
        if success:
            self._metrics.milestone_success += 1

    def record_duration(self, *, total: float | None = None, model: float | None = None, tool: float | None = None) -> None:
        if total is not None:
            self._metrics.total_duration += total
        if model is not None:
            self._metrics.model_duration += model
        if tool is not None:
            self._metrics.tool_duration += tool

    def record_budget(self, budget_stats: dict[str, Any] | None) -> None:
        if not budget_stats:
            return
        tokens_used = budget_stats.get("tokens_used")
        if tokens_used is not None:
            self._metrics.budget_tokens_used = _coerce_int(tokens_used)
        tokens_limit = budget_stats.get("tokens_limit")
        if tokens_limit is not None:
            self._metrics.budget_tokens_limit = _coerce_int(tokens_limit)
        cost_used = budget_stats.get("cost_used")
        if cost_used is not None:
            try:
                self._metrics.budget_cost_used = float(cost_used)
            except (TypeError, ValueError):
                pass

    def record_error(self, error: Exception | str | None) -> None:
        if error is None:
            return
        self._metrics.errors_total += 1
        error_type = type(error).__name__ if isinstance(error, Exception) else "error"
        self._metrics.errors_by_type[error_type] = self._metrics.errors_by_type.get(error_type, 0) + 1


__all__ = ["MetricsCollector"]
