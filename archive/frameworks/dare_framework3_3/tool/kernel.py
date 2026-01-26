"""Tool domain kernel interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence

from dare_framework3_3.tool.types import CapabilityDescriptor, ExecutionSignal

if TYPE_CHECKING:
    from dare_framework3_3.plan.types import Envelope


class IToolGateway(Protocol):
    """[Kernel] Capability invocation boundary.

    Usage: Called by the agent to list and invoke capabilities across providers.
    """

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        """[Kernel] List available capabilities across providers.

        Usage: Called to build a catalog for planners and validation.
        """
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        """[Kernel] Invoke a capability within an execution envelope.

        Usage: Called by the agent execution layer after validation.
        """
        ...

    def register_provider(self, provider: object) -> None:
        """[Kernel] Register a capability provider.

        Usage: Called during setup to attach providers implementing ICapabilityProvider.
        """
        ...


class IExecutionControl(Protocol):
    """[Kernel] Pause/resume/checkpoint control plane.

    Usage: Called by the agent loop to coordinate execution control signals.
    """

    def poll(self) -> ExecutionSignal:
        """[Kernel] Poll for control signals.

        Usage: Called frequently during execution to detect pauses/cancels.
        """
        ...

    def poll_or_raise(self) -> None:
        """[Kernel] Raise a standardized exception for non-NONE signals.

        Usage: Called by execution loops to handle control flow uniformly.
        """
        ...

    async def pause(self, reason: str) -> str:
        """[Kernel] Enter PAUSED state and create a checkpoint.

        Usage: Called when user or policy requests a pause.
        """
        ...

    async def resume(self, checkpoint_id: str) -> None:
        """[Kernel] Resume execution from a checkpoint.

        Usage: Called after human approval or resume signal.
        """
        ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        """[Kernel] Create a checkpoint with attached payload.

        Usage: Called to persist execution state snapshots.
        """
        ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        """[Kernel] Request human approval for a checkpoint.

        Usage: Called when HITL approval is required.
        """
        ...


__all__ = ["IToolGateway", "IExecutionControl"]
