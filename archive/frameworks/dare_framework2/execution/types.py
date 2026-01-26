"""Execution domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Sequence
from uuid import uuid4

if TYPE_CHECKING:
    pass


# =============================================================================
# Run Loop State
# =============================================================================

class RunLoopState(Enum):
    """Tick-based run loop states.
    
    Values:
        IDLE: Not running
        PLANNING: Generating a plan
        EXECUTING: Executing steps
        VALIDATING: Verifying results
        PAUSED: Temporarily paused
        WAITING_HUMAN: Waiting for human approval
        COMPLETED: Successfully completed
        ABORTED: Terminated with errors
    """
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass(frozen=True)
class TickResult:
    """Result of a single scheduling tick.
    
    Debug/visualization friendly representation of one step.
    
    Attributes:
        state: Current run loop state
        produced_event_ids: Event IDs produced during this tick
        completed: Whether execution is complete
    """
    state: RunLoopState
    produced_event_ids: list[str] = field(default_factory=list)
    completed: bool = False


# =============================================================================
# Execution Control
# =============================================================================

class ExecutionSignal(Enum):
    """Signals used by the Kernel to pause/cancel or request HITL.
    
    Values:
        NONE: No signal
        PAUSE_REQUESTED: Pause has been requested
        CANCEL_REQUESTED: Cancellation has been requested
        HUMAN_APPROVAL_REQUIRED: Human approval is required
    """
    NONE = "none"
    PAUSE_REQUESTED = "pause_requested"
    CANCEL_REQUESTED = "cancel_requested"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"


class PauseRequested(RuntimeError):
    """Raised by poll_or_raise when the control plane requests a pause."""


class CancelRequested(RuntimeError):
    """Raised by poll_or_raise when the control plane requests cancellation."""


class HumanApprovalRequired(RuntimeError):
    """Raised by poll_or_raise when HITL approval is required."""


@dataclass(frozen=True)
class Checkpoint:
    """Checkpoint metadata for pause/resume functionality.
    
    Captures minimum information for aligning checkpoints with
    the EventLog for replay/audit.
    
    Attributes:
        id: Unique checkpoint identifier
        created_at: Unix timestamp of creation
        event_id: Corresponding event log entry
        snapshot_ref: Optional reference to snapshot storage
        note: Optional human-readable note
    """
    id: str
    created_at: float
    event_id: str
    snapshot_ref: str | None = None
    note: str | None = None


# =============================================================================
# Budget and Resources
# =============================================================================

class ResourceType(Enum):
    """Canonical resource types for budget accounting.
    
    Values:
        TOKENS: LLM tokens
        COST: Monetary cost
        TIME_SECONDS: Wall clock time
        TOOL_CALLS: Number of tool invocations
    """
    TOKENS = "tokens"
    COST = "cost"
    TIME_SECONDS = "time_seconds"
    TOOL_CALLS = "tool_calls"


@dataclass(frozen=True)
class Budget:
    """Coarse-grained budgets for a scope or envelope.
    
    The initial implementation may enforce only a subset
    (e.g., tool calls / time), but all fields are exposed.
    
    Attributes:
        max_tokens: Maximum tokens allowed
        max_cost: Maximum cost allowed
        max_time_seconds: Maximum execution time
        max_tool_calls: Maximum tool invocations
    """
    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None


class ResourceExhausted(RuntimeError):
    """Raised when a budget limit is exceeded."""


# =============================================================================
# Event Log
# =============================================================================

@dataclass(frozen=True)
class Event:
    """Append-only event record used for audit and replay (WORM).
    
    Attributes:
        event_type: Type of event (e.g., "task.start", "tool.invoke")
        payload: Event data
        event_id: Unique event identifier
        timestamp: Event timestamp
        prev_hash: Hash of previous event (for chain integrity)
        event_hash: Hash of this event
    """
    event_type: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prev_hash: str | None = None
    event_hash: str | None = None


@dataclass(frozen=True)
class RuntimeSnapshot:
    """A minimal replay snapshot produced from the event log.
    
    Used for debugging and verification.
    
    Attributes:
        from_event_id: Starting event ID
        events: Events in the snapshot
    """
    from_event_id: str
    events: Sequence[Event]


# =============================================================================
# Hook Phase
# =============================================================================

class HookPhase(Enum):
    """Kernel hook phases for extension points.
    
    Values:
        BEFORE_PLAN: Before planning starts
        AFTER_PLAN: After planning completes
        BEFORE_TOOL: Before tool execution
        AFTER_TOOL: After tool execution
        BEFORE_VERIFY: Before verification
        AFTER_VERIFY: After verification
    """
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"
