"""Default ExecutionControl implementation.

Provides HITL (human-in-the-loop) control plane for pause/resume/checkpoint.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from dare_framework.tool.interfaces import IExecutionControl
from dare_framework.tool.types import ExecutionSignal


@dataclass
class Checkpoint:
    """Represents a saved execution checkpoint."""

    checkpoint_id: str
    label: str
    payload: dict[str, Any]
    created_at: float
    resumed: bool = False


class DefaultExecutionControl(IExecutionControl):
    """Default implementation of IExecutionControl.
    
    V4 alignment:
    - Supports pause/resume/checkpoint for HITL workflows
    - Manages ExecutionSignal state
    - Provides wait_for_human for explicit human approval points
    """

    def __init__(self) -> None:
        self._signal: ExecutionSignal = ExecutionSignal.NONE
        self._checkpoints: dict[str, Checkpoint] = {}
        self._pending_approval: set[str] = set()
        self._approval_events: dict[str, asyncio.Event] = {}

    def poll(self) -> ExecutionSignal:
        """Poll current execution signal.
        
        Returns:
            Current execution signal state.
        """
        return self._signal

    def poll_or_raise(self) -> None:
        """Poll and raise if signal indicates interruption.
        
        Raises:
            InterruptedError: If pause or cancel is requested.
            PermissionError: If human approval is required.
        """
        if self._signal == ExecutionSignal.PAUSE_REQUESTED:
            raise InterruptedError("Pause requested")
        if self._signal == ExecutionSignal.CANCEL_REQUESTED:
            raise InterruptedError("Cancel requested")
        if self._signal == ExecutionSignal.HUMAN_APPROVAL_REQUIRED:
            raise PermissionError("Human approval required")

    async def pause(self, reason: str) -> str:
        """Pause execution and create a checkpoint.
        
        Args:
            reason: Reason for pausing.
            
        Returns:
            Checkpoint ID for resuming.
        """
        self._signal = ExecutionSignal.PAUSE_REQUESTED
        checkpoint_id = await self.checkpoint(label="pause", payload={"reason": reason})
        return checkpoint_id

    async def resume(self, checkpoint_id: str) -> None:
        """Resume execution from a checkpoint.
        
        Args:
            checkpoint_id: The checkpoint to resume from.
            
        Raises:
            KeyError: If checkpoint not found.
        """
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint not found: {checkpoint_id}")
        
        self._checkpoints[checkpoint_id].resumed = True
        self._signal = ExecutionSignal.NONE
        
        # Release any waiting approval
        if checkpoint_id in self._approval_events:
            self._approval_events[checkpoint_id].set()
            self._pending_approval.discard(checkpoint_id)

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        """Create a checkpoint.
        
        Args:
            label: Label for the checkpoint.
            payload: Data to store in the checkpoint.
            
        Returns:
            Checkpoint ID.
        """
        checkpoint_id = str(uuid.uuid4())
        self._checkpoints[checkpoint_id] = Checkpoint(
            checkpoint_id=checkpoint_id,
            label=label,
            payload=payload,
            created_at=time.time(),
        )
        return checkpoint_id

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        """Wait for human approval at a checkpoint.
        
        Args:
            checkpoint_id: The checkpoint requiring approval.
            reason: Reason for requiring approval.
            
        Raises:
            KeyError: If checkpoint not found.
        """
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint not found: {checkpoint_id}")
        
        self._signal = ExecutionSignal.HUMAN_APPROVAL_REQUIRED
        self._pending_approval.add(checkpoint_id)
        
        # Create an event to wait on
        event = asyncio.Event()
        self._approval_events[checkpoint_id] = event
        
        # Wait for resume to be called
        await event.wait()
        
        # Clean up
        del self._approval_events[checkpoint_id]

    def request_cancel(self) -> None:
        """Request cancellation of current execution."""
        self._signal = ExecutionSignal.CANCEL_REQUESTED

    def clear_signal(self) -> None:
        """Clear the current signal."""
        self._signal = ExecutionSignal.NONE

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Get a checkpoint by ID.
        
        Args:
            checkpoint_id: The checkpoint ID.
            
        Returns:
            The checkpoint or None if not found.
        """
        return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints.
        
        Returns:
            List of all checkpoints.
        """
        return list(self._checkpoints.values())

    def is_pending_approval(self, checkpoint_id: str) -> bool:
        """Check if a checkpoint is pending approval.
        
        Args:
            checkpoint_id: The checkpoint ID.
            
        Returns:
            True if pending approval, False otherwise.
        """
        return checkpoint_id in self._pending_approval


__all__ = ["Checkpoint", "DefaultExecutionControl"]
