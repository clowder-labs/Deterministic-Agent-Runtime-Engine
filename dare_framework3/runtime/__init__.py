"""Runtime domain: how the Agent runs.

This domain handles the runtime control of agent execution,
including checkpointing, budgets, event logging, and hooks.

Note: IRunLoop and ILoopOrchestrator have been removed in v3.1.
Their responsibilities are now handled by Agent classes directly.

Factory Functions:
    create_default_resource_manager: Create default IResourceManager
    create_default_event_log: Create default IEventLog
    create_default_execution_control: Create default IExecutionControl
    create_default_extension_point: Create default IExtensionPoint
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3.runtime.interfaces import (
    IExecutionControl,
    IResourceManager,
    IEventLog,
    IExtensionPoint,
    IHook,
)
from dare_framework3.runtime.types import (
    # Execution control
    ExecutionSignal,
    PauseRequested,
    CancelRequested,
    HumanApprovalRequired,
    Checkpoint,
    # Budget
    ResourceType,
    Budget,
    ResourceExhausted,
    # Event log
    Event,
    RuntimeSnapshot,
    # Hook
    HookPhase,
)

if TYPE_CHECKING:
    pass

__all__ = [
    # Interfaces
    "IExecutionControl",
    "IResourceManager",
    "IEventLog",
    "IExtensionPoint",
    "IHook",
    # Execution control
    "ExecutionSignal",
    "PauseRequested",
    "CancelRequested",
    "HumanApprovalRequired",
    "Checkpoint",
    # Budget
    "ResourceType",
    "Budget",
    "ResourceExhausted",
    # Event log
    "Event",
    "RuntimeSnapshot",
    # Hook
    "HookPhase",
    # Factory functions
    "create_default_resource_manager",
    "create_default_event_log",
    "create_default_execution_control",
    "create_default_extension_point",
]


# =============================================================================
# Factory Functions (resolve DIP: high-level modules don't import impl directly)
# =============================================================================

def create_default_resource_manager(
    budget: Budget | None = None,
) -> IResourceManager:
    """Create the default IResourceManager implementation.
    
    Args:
        budget: Default budget for the manager. If None, uses sensible defaults.
        
    Returns:
        An InMemoryResourceManager instance
    """
    from dare_framework3.runtime.impl.in_memory_resource_manager import InMemoryResourceManager
    return InMemoryResourceManager(default_budget=budget)


def create_default_event_log(
    path: str,
) -> IEventLog:
    """Create the default IEventLog implementation.
    
    Args:
        path: Path to the event log file (JSONL format)
        
    Returns:
        A LocalEventLog instance
    """
    from dare_framework3.runtime.impl.local_event_log import LocalEventLog
    return LocalEventLog(path=path)


def create_default_execution_control(
    event_log: IEventLog | None = None,
    checkpoint_dir: str = ".dare/checkpoints",
) -> IExecutionControl:
    """Create the default IExecutionControl implementation.
    
    Args:
        event_log: Event log for recording checkpoints
        checkpoint_dir: Directory for storing checkpoint files
        
    Returns:
        A FileExecutionControl instance
    """
    from dare_framework3.runtime.impl.file_execution_control import FileExecutionControl
    return FileExecutionControl(event_log=event_log, checkpoint_dir=checkpoint_dir)


def create_default_extension_point() -> IExtensionPoint:
    """Create the default IExtensionPoint implementation.
    
    Returns:
        A DefaultExtensionPoint instance
    """
    from dare_framework3.runtime.impl.default_extension_point import DefaultExtensionPoint
    return DefaultExtensionPoint()
