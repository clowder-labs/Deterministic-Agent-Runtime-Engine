"""Context storage for telemetry correlation identifiers."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TelemetryIds:
    trace_id: str
    span_id: str


_TELEMETRY_STACK: ContextVar[tuple[TelemetryIds, ...]] = ContextVar(
    "dare_telemetry_stack",
    default=(),
)


def push_ids(trace_id: str, span_id: str) -> None:
    stack = list(_TELEMETRY_STACK.get())
    stack.append(TelemetryIds(trace_id=trace_id, span_id=span_id))
    _TELEMETRY_STACK.set(tuple(stack))


def pop_ids() -> None:
    stack = list(_TELEMETRY_STACK.get())
    if stack:
        stack.pop()
    _TELEMETRY_STACK.set(tuple(stack))


def current_ids() -> TelemetryIds | None:
    stack = _TELEMETRY_STACK.get()
    return stack[-1] if stack else None


def stack_ids() -> Iterable[TelemetryIds]:
    return _TELEMETRY_STACK.get()


__all__ = ["TelemetryIds", "push_ids", "pop_ids", "current_ids", "stack_ids"]
