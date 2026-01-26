"""Execution domain kernel interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Protocol, Sequence

from dare_framework2.execution.types import (
    RunLoopState,
    TickResult,
    ExecutionSignal,
    Budget,
    ResourceType,
    Event,
    RuntimeSnapshot,
    HookPhase,
)

if TYPE_CHECKING:
    from dare_framework2.plan.types import (
        Task,
        Milestone,
        ValidatedPlan,
        ToolLoopRequest,
        RunResult,
        MilestoneResult,
        ExecuteResult,
        ToolLoopResult,
    )


# =============================================================================
# Run Loop Interface
# =============================================================================

class IRunLoop(Protocol):
    """Tick-based run surface for the Kernel.
    
    Provides both tick-by-tick execution for debugging/visualization
    and full run execution for production use.
    """

    @property
    def state(self) -> RunLoopState:
        """Current run loop state."""
        ...

    async def tick(self) -> TickResult:
        """Execute a minimal scheduling step.
        
        Enables debugging/visualization of execution progress.
        
        Returns:
            Result of this tick including state and events
        """
        ...

    async def run(self, task: "Task") -> "RunResult":
        """Drive execution until termination.
        
        Internally calls tick() repeatedly until complete.
        
        Args:
            task: The task to execute
            
        Returns:
            Final execution result
        """
        ...


# =============================================================================
# Loop Orchestrator Interface
# =============================================================================

class ILoopOrchestrator(Protocol):
    """Five-layer loop skeleton.
    
    Orchestrates the Session -> Milestone -> Plan -> Execute -> Tool loop.
    """

    async def run_session_loop(self, task: "Task") -> "RunResult":
        """Run the session loop for a task.
        
        The outermost loop that manages the full task lifecycle.
        """
        ...

    async def run_milestone_loop(self, milestone: "Milestone") -> "MilestoneResult":
        """Run the milestone loop.
        
        Executes a single milestone with retry/remediation.
        """
        ...

    async def run_plan_loop(self, milestone: "Milestone") -> "ValidatedPlan":
        """Run the plan loop.
        
        Generates and validates a plan for a milestone.
        """
        ...

    async def run_execute_loop(self, plan: "ValidatedPlan") -> "ExecuteResult":
        """Run the execute loop.
        
        Executes validated plan steps.
        """
        ...

    async def run_tool_loop(self, req: "ToolLoopRequest") -> "ToolLoopResult":
        """Run the tool loop.
        
        Executes a tool within its envelope constraints.
        """
        ...


# =============================================================================
# Execution Control Interface
# =============================================================================

class IExecutionControl(Protocol):
    """Pause/resume/checkpoint control plane.
    
    Enables external control over execution, including pausing,
    resuming, checkpointing, and human-in-the-loop integration.
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
# Resource Manager Interface
# =============================================================================

class IResourceManager(Protocol):
    """Unified budget model and accounting.
    
    Tracks resource consumption against budgets and raises
    ResourceExhausted when limits are exceeded.
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
# Event Log Interface
# =============================================================================

class IEventLog(Protocol):
    """WORM truth source for audit and replay."""

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
# Extension Point Interface
# =============================================================================

class IExtensionPoint(Protocol):
    """System-level extension point for emitting hooks."""

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

