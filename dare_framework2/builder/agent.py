"""Agent class - the developer-facing wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework2.plan.types import Task, RunResult

if TYPE_CHECKING:
    from dare_framework2.execution.interfaces import IRunLoop
    from dare_framework2.tool.impl.run_context_state import RunContextState


class Agent:
    """Developer-facing agent wrapper around the Kernel run loop.
    
    Provides a simple interface for running tasks with the DARE framework.
    
    Args:
        run_loop: The run loop instance to use for execution
        run_context: The run context state for passing dependencies
    """

    def __init__(
        self,
        *,
        run_loop: "IRunLoop",
        run_context: "RunContextState",
    ) -> None:
        self._run_loop = run_loop
        self._run_context = run_context

    async def run(
        self,
        task: str | Task,
        deps: Any | None = None,
    ) -> RunResult:
        """Run a task and return the result.
        
        Args:
            task: The task to run (string description or Task object)
            deps: Optional dependencies to make available to tools
            
        Returns:
            The execution result
        """
        # deps is stored outside Task to keep Task serializable and audit-friendly
        self._run_context.deps = deps
        task_obj = task if isinstance(task, Task) else Task(description=task)
        return await self._run_loop.run(task_obj)
