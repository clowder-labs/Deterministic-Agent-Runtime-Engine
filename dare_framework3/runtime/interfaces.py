"""Runtime domain interfaces.

This module contains the core Kernel interfaces for runtime infrastructure:
- IExecutionControl: Pause/resume/checkpoint control
- IResourceManager: Budget and resource accounting
- IEventLog: Audit logging and replay
- IExtensionPoint: Hook registration and emission
- IHook: Individual hook callbacks

Note: IRunLoop and ILoopOrchestrator have been removed in v3.1.
Their responsibilities are now handled by Agent._execute() and FiveLayerAgent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Protocol, Sequence

from dare_framework3.runtime.types import (
    ExecutionSignal,
    Budget,
    ResourceType,
    Event,
    RuntimeSnapshot,
    HookPhase,
)

if TYPE_CHECKING:
    pass  # No TYPE_CHECKING imports needed after removing orchestrator interfaces


# =============================================================================
# Execution Control Interface (Layer 0 Kernel)
# =============================================================================

class IExecutionControl(Protocol):
    """Pause/resume/checkpoint control plane.
    
    Enables external control over execution, including pausing,
    resuming, checkpointing, and human-in-the-loop integration.
    
    This is a Layer 0 Kernel interface.
    """

    def poll(self) -> ExecutionSignal:
        """Poll for control signals.
        
        Returns:
            Current execution signal (NONE if no signal)
        """
        ...

    def poll_or_raise(self) -> None:
        """Raise a standardized exception for non-NONE signals.
        
        Raises:
            PauseRequested: If pause was requested
            CancelRequested: If cancellation was requested
            HumanApprovalRequired: If human approval is required
        """
        ...

    async def pause(self, reason: str) -> str:
        """Enter PAUSED state and create a checkpoint.
        
        Args:
            reason: Human-readable pause reason
            
        Returns:
            Checkpoint ID
        """
        ...

    async def resume(self, checkpoint_id: str) -> None:
        """Resume from a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to resume from
        """
        ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        """Create an explicit checkpoint with attached payload.
        
        Args:
            label: Checkpoint label
            payload: Checkpoint data
            
        Returns:
            Checkpoint ID
        """
        ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        """Request/record a HITL waiting point.
        
        The architecture requires an explicit "waiting" control-plane call
        after pausing for approval. MVP implementations may be non-blocking.
        
        Args:
            checkpoint_id: Associated checkpoint ID
            reason: Reason for human approval
        """
        ...


# =============================================================================
# Resource Manager Interface (Layer 0 Kernel)
# =============================================================================

class IResourceManager(Protocol):
    """Unified budget model and accounting.
    
    Tracks resource consumption against budgets and raises
    ResourceExhausted when limits are exceeded.
    
    This is a Layer 0 Kernel interface.
    """

    def get_budget(self, scope: str) -> Budget:
        """Get the budget for a scope.
        
        Args:
            scope: Budget scope identifier
            
        Returns:
            Budget for the scope
        """
        ...

    def acquire(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        """Reserve resources for a scope.
        
        Args:
            resource: Type of resource
            amount: Amount to acquire
            scope: Budget scope
            
        Raises:
            ResourceExhausted: If budget would be exceeded
        """
        ...

    def record(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        """Record consumption for audit and feedback loops.
        
        Args:
            resource: Type of resource
            amount: Amount consumed
            scope: Budget scope
        """
        ...

    def check_limit(self, *, scope: str) -> None:
        """Check if scope is within budget.
        
        Args:
            scope: Budget scope
            
        Raises:
            ResourceExhausted: If scope is over budget
        """
        ...


# =============================================================================
# Event Log Interface (Layer 0 Kernel)
# =============================================================================

class IEventLog(Protocol):
    """WORM truth source for audit and replay.
    
    This is a Layer 0 Kernel interface.
    """

    async def append(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Append an event to the log.
        
        Args:
            event_type: Type of event
            payload: Event data
            
        Returns:
            Event ID
        """
        ...

    async def query(
        self,
        *,
        filter: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> Sequence[Event]:
        """Query events from the log.
        
        Args:
            filter: Optional filter criteria
            limit: Maximum events to return
            
        Returns:
            Matching events
        """
        ...

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        """Create a replay snapshot from an event.
        
        Args:
            from_event_id: Starting event ID
            
        Returns:
            Runtime snapshot for replay
        """
        ...

    async def verify_chain(self) -> bool:
        """Verify the integrity of the event chain.
        
        Returns:
            True if chain is valid
        """
        ...


# =============================================================================
# Extension Point Interface (Layer 0 Kernel)
# =============================================================================

class IExtensionPoint(Protocol):
    """System-level extension point for emitting hooks.
    
    This is a Layer 0 Kernel interface.
    """

    def register_hook(
        self,
        phase: HookPhase,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a hook callback for a phase.
        
        Args:
            phase: Hook phase to register for
            callback: Callback function
        """
        ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        """Emit a hook event.
        
        Args:
            phase: Hook phase
            payload: Hook data
        """
        ...


# =============================================================================
# Hook Interface (Layer 2 Component)
# =============================================================================

class IHook(Protocol):
    """A single hook callback bound to a Kernel phase.
    
    Hooks are Layer 2 components that can be registered with the
    IExtensionPoint to receive callbacks at specific execution phases.
    """

    @property
    def phase(self) -> HookPhase:
        """The phase this hook is bound to."""
        ...

    def __call__(self, payload: dict[str, Any]) -> Any:
        """Execute the hook.
        
        Args:
            payload: Hook data
            
        Returns:
            Hook result (may be async)
        """
        ...
