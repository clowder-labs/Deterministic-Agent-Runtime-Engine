"""Composite extension point implementation.

This helper composes multiple `IExtensionPoint` instances into one so callers
can treat a fan-out set of extension points as a single kernel surface.
"""

from __future__ import annotations

from typing import Any

from dare_framework.hook.kernel import IExtensionPoint


class CompositeExtensionPoint(IExtensionPoint):
    """Fan-out extension point that emits to multiple extension points in order."""

    def __init__(self, extension_points: list[IExtensionPoint]) -> None:
        self._extension_points = list(extension_points)

    def register_hook(self, phase: Any, hook: Any) -> None:
        for extension_point in self._extension_points:
            extension_point.register_hook(phase, hook)

    async def emit(self, phase: Any, payload: dict[str, Any]) -> None:
        for extension_point in self._extension_points:
            await extension_point.emit(phase, payload)


__all__ = ["CompositeExtensionPoint"]
