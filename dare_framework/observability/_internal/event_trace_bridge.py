"""Bridge between EventLog and OpenTelemetry traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.trace import format_span_id, format_trace_id

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OTEL_AVAILABLE = False

from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event, RuntimeSnapshot


@dataclass
class TraceContext:
    """OpenTelemetry trace context."""

    trace_id: str
    span_id: str | None = None
    trace_flags: int = 0


def extract_trace_context() -> TraceContext | None:
    """Extract trace context from current OTel context."""
    if not OTEL_AVAILABLE:
        return None

    ctx = trace.get_current_span().get_span_context()
    is_valid_attr = getattr(ctx, "is_valid", None)
    is_valid = is_valid_attr() if callable(is_valid_attr) else bool(is_valid_attr)
    if not is_valid:
        return None

    return TraceContext(
        trace_id=format_trace_id(ctx.trace_id),
        span_id=format_span_id(ctx.span_id),
        trace_flags=ctx.trace_flags,
    )


class TraceAwareEventLog(IEventLog):
    """EventLog that automatically captures trace context."""

    def __init__(self, inner_event_log: IEventLog) -> None:
        self._inner = inner_event_log

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        trace_ctx = extract_trace_context()
        enhanced_payload = dict(payload or {})
        if trace_ctx:
            enhanced_payload["_trace"] = {
                "trace_id": trace_ctx.trace_id,
                "span_id": trace_ctx.span_id,
                "trace_flags": trace_ctx.trace_flags,
            }

        event_id = await self._inner.append(event_type, enhanced_payload)

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
        return list(await self._inner.query(filter=filter, limit=limit))

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        return await self._inner.replay(from_event_id=from_event_id)

    async def verify_chain(self) -> bool:
        return await self._inner.verify_chain()


def make_trace_aware(event_log: IEventLog | None) -> IEventLog | None:
    """Make an event log trace-aware."""
    if event_log is None:
        return None
    if isinstance(event_log, TraceAwareEventLog):
        return event_log
    return TraceAwareEventLog(event_log)


__all__ = [
    "TraceContext",
    "extract_trace_context",
    "TraceAwareEventLog",
    "make_trace_aware",
]
