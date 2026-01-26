"""Kernel execution control protocols (v2)."""

from __future__ import annotations

from typing import Protocol

from dare_framework.execution.impl.execution_control.models import ExecutionSignal


class IExecutionControl(Protocol):
    """Pause/resume/checkpoint control plane (v2.0)."""

    def poll(self) -> ExecutionSignal: ...

    def poll_or_raise(self) -> None:
        """Raise a standardized exception for non-NONE signals."""

    async def pause(self, reason: str) -> str:
        """Enter PAUSED and create a checkpoint; returns checkpoint id."""

    async def resume(self, checkpoint_id: str) -> None:
        """Resume from a checkpoint."""

    async def checkpoint(self, label: str, payload: dict) -> str:
        """Create an explicit checkpoint with an attached payload."""

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        """Request/record a HITL waiting point.

        The v2.0 architecture requires an explicit "waiting" control-plane call after
        pausing for approval. MVP implementations MAY be non-blocking (for example,
        recording an audit event and returning immediately) as long as the interface
        exists and the orchestrator wires it into approval-required paths.
        """
