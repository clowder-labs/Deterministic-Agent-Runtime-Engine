"""Observability domain stable interfaces."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.hook.kernel import IHook


class ITelemetryProvider(IHook, Protocol):
    """[Component] Telemetry provider that consumes runtime emissions."""

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Handle a runtime event log emission."""
        ...

    async def shutdown(self) -> None:
        """Flush and shutdown the provider."""
        ...


__all__ = ["ITelemetryProvider"]
