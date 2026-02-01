"""No-op telemetry provider."""

from __future__ import annotations

from typing import Any, Literal

from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.observability.kernel import ITelemetryProvider


class NoopTelemetryProvider(ITelemetryProvider):
    """Telemetry provider that drops all emissions."""

    name = "noop-telemetry"

    @property
    def component_type(self) -> Literal[ComponentType.TELEMETRY]:
        return ComponentType.TELEMETRY

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> None:
        return None

    async def on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        return None

    async def shutdown(self) -> None:
        return None


__all__ = ["NoopTelemetryProvider"]
