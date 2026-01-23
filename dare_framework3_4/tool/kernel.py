"""tool domain stable interfaces (Kernel boundaries).

v4.0 alignment notes:
- All side-effects MUST flow through `IToolGateway.invoke(...)`.
- HITL control plane lives behind `IExecutionControl`.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework3_4.plan.types import Envelope
from dare_framework3_4.tool.types import CapabilityDescriptor, ExecutionSignal


class IToolGateway(Protocol):
    """System-call boundary and trusted capability registry facade."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: Envelope,
    ) -> Any: ...

    def register_provider(self, provider: object) -> None: ...


class IExecutionControl(Protocol):
    """Control plane for pause/resume/checkpoints (HITL)."""

    def poll(self) -> ExecutionSignal: ...

    def poll_or_raise(self) -> None: ...

    async def pause(self, reason: str) -> str: ...

    async def resume(self, checkpoint_id: str) -> None: ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str: ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None: ...


__all__ = ["IExecutionControl", "IToolGateway"]

