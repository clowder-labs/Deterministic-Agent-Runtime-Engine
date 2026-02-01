"""Default extension point implementation that dispatches to hooks."""

from __future__ import annotations

import logging
from typing import Any

from dare_framework.hook.kernel import HookFn, IExtensionPoint, IHook
from dare_framework.hook.types import HookPhase

_logger = logging.getLogger("dare.hook")


class HookExtensionPoint(IExtensionPoint):
    """Dispatch hook payloads to registered hook functions and components."""

    def __init__(self, hooks: list[IHook] | None = None) -> None:
        self._hooks = list(hooks) if hooks is not None else []
        self._callbacks: dict[HookPhase, list[HookFn]] = {}

    def register_hook(self, phase: HookPhase, hook: HookFn) -> None:
        self._callbacks.setdefault(phase, []).append(hook)

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        callbacks = list(self._callbacks.get(phase, []))
        for callback in callbacks:
            try:
                callback(payload)
            except Exception as exc:
                _logger.exception("Hook callback failed: %s", exc)

        for hook in self._hooks:
            try:
                await hook.invoke(phase, payload=payload)
            except Exception as exc:
                _logger.exception("Hook component failed: %s", exc)


__all__ = ["HookExtensionPoint"]
