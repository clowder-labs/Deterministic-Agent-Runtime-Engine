"""Execution domain: how the Agent runs.

This domain handles the runtime control of agent execution,
including the run loop, orchestration, checkpointing, budgets,
event logging, and hooks.
"""

from dare_framework2.execution.interfaces import (
    IRunLoop,
    ILoopOrchestrator,
    IExecutionControl,
    IResourceManager,
    IEventLog,
    IExtensionPoint,
    IHook,
)
from dare_framework2.execution.types import (
    # Run loop
    RunLoopState,
    TickResult,
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

__all__ = [
    # Interfaces
    "IRunLoop",
    "ILoopOrchestrator",
    "IExecutionControl",
    "IResourceManager",
    "IEventLog",
    "IExtensionPoint",
    "IHook",
    # Run loop
    "RunLoopState",
    "TickResult",
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
]
