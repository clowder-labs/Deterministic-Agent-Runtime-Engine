"""Observability domain kernel interfaces."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Literal, Protocol, runtime_checkable

from dare_framework.infra.component import ComponentType


@runtime_checkable
class ITelemetryProvider(Protocol):
    """[Kernel] Unified telemetry provider for traces, metrics, and logs."""

    @property
    def name(self) -> str:
        """Provider name used for identification."""
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
        """Start a new span for tracing."""
        ...

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric value."""
        ...

    def record_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record an event on the current span."""
        ...

    def shutdown(self) -> None:
        """Flush and shutdown the provider."""
        ...


@runtime_checkable
class ISpan(Protocol):
    """[Kernel] Span interface for distributed tracing."""

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
