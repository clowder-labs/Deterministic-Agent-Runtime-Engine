from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Protocol


class HookPhase(Enum):
    """Kernel hook phases (v2.0)."""

    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"


class IExtensionPoint(Protocol):
    """System-level extension point for emitting hooks (v2.0)."""

    def register_hook(self, phase: HookPhase, callback: Callable[[dict[str, Any]], Any]) -> None: ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None: ...
