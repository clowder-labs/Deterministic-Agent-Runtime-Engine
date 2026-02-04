"""tool domain pluggable interfaces (implementations).

This module declares non-kernel contracts; core tool interfaces live in
`dare_framework.tool.kernel`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework.tool.types import ExecutionSignal


@runtime_checkable
class IExecutionControl(Protocol):
    """Control plane for pause/resume/checkpoints (HITL)."""

    def poll(self) -> ExecutionSignal: ...

    def poll_or_raise(self) -> None: ...

    async def pause(self, reason: str) -> str: ...

    async def resume(self, checkpoint_id: str) -> None: ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str: ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None: ...


__all__ = [
    "IExecutionControl",
]
