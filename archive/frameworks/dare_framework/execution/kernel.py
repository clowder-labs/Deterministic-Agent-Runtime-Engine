"""Execution domain kernel interfaces."""

from dare_framework.execution.impl.budget.protocols import IResourceManager
from dare_framework.execution.impl.event.protocols import IEventLog
from dare_framework.execution.impl.execution_control.protocols import IExecutionControl
from dare_framework.execution.impl.hook.protocols import IExtensionPoint
from dare_framework.execution.impl.orchestrator.protocols import ILoopOrchestrator
from dare_framework.execution.impl.run_loop.protocols import IRunLoop

__all__ = [
    "IRunLoop",
    "ILoopOrchestrator",
    "IExecutionControl",
    "IResourceManager",
    "IEventLog",
    "IExtensionPoint",
]
