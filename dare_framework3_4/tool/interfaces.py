"""Tool domain interfaces for v4.0."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence

from dare_framework3_4.tool.types import CapabilityDescriptor, ExecutionSignal

if TYPE_CHECKING:
    from dare_framework3_4.plan.types import Envelope


class IToolGateway(Protocol):
    """System-call boundary: all side effects flow through invoke()."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        """Return the trusted capability registry."""
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        """Invoke a capability within the execution envelope."""
        ...

    def register_provider(self, provider: object) -> None:
        """Register a capability provider."""
        ...


class IExecutionControl(Protocol):
    """Execution control plane for pause/resume/HITL."""

    def poll(self) -> ExecutionSignal:
        ...

    def poll_or_raise(self) -> None:
        ...

    async def pause(self, reason: str) -> str:
        ...

    async def resume(self, checkpoint_id: str) -> None:
        ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        ...


__all__ = ["IToolGateway", "IExecutionControl"]
