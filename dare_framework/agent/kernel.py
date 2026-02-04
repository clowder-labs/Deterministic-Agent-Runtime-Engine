"""agent domain stable interfaces.

Alignment note:
- The minimal runtime surface is `IAgent.run(...)` (orchestration is an agent concern).

Design Decision (2026-01-30):
    The `IAgent.run()` method accepts both `str` and `Task` for flexibility:
    
    - **Simple usage**: Pass a string for basic task execution (ReAct or simple mode).
    - **Advanced usage**: Pass a `Task` object with pre-defined `milestones` for
      full five-layer orchestration mode.
    
    While `Task.milestones` is technically an orchestration concept, keeping it in the
    `IAgent` interface provides a unified entry point. The agent implementation
    (e.g., DareAgent) internally routes to the appropriate execution mode based on
    whether milestones are present and whether a planner is configured.
    
    See: docs/用户旅程地图：全栈智能研发 Agent 交付云服务 LandingZone 对接.md
"""

from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING

from dare_framework.plan.types import RunResult, Task

if TYPE_CHECKING:
    from dare_framework.transport.kernel import AgentChannel


class IAgent(Protocol):
    """Framework minimal runtime surface.

    This is the single entry point for executing tasks with an agent.
    The interface supports multiple execution modes through a unified API:

    Execution Modes:
        1. **Simple Mode** (str input, no tools):
           Agent generates a response using only the model.
        
        2. **ReAct Mode** (str input, with tools):
           Agent uses tools in a reasoning loop without explicit planning.
        
        3. **Five-Layer Mode** (Task with milestones, or with planner):
           Full orchestration with Session → Milestone → Plan → Execute → Tool loops.

    Example:
        # Simple string input (auto-routed based on agent config)
        result = await agent.run("Explain this codebase")

        # Task object for advanced control
        task = Task(
            description="Implement feature X",
            milestones=[
                Milestone(milestone_id="m1", description="Design API"),
                Milestone(milestone_id="m2", description="Write tests"),
            ],
        )
        result = await agent.run(task)
    """

    async def __call__(self, message: str | Task, deps: Any | None = None) -> RunResult:
        """Invoke the agent directly (no transport attached)."""
        ...

    async def start(self) -> None:
        """Start agent components and spawn the transport loop if configured."""
        ...

    async def stop(self) -> None:
        """Stop agent components and cancel the transport loop."""
        ...

    async def run(
        self,
        task: str | Task,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute a task and return a structured RunResult.

        Args:
            task: Either a simple string description or a Task object.
                - **str**: Treated as task description, auto-wrapped into Task.
                - **Task**: Used directly. If `milestones` are present, enables
                  full five-layer orchestration; otherwise routes based on
                  agent configuration (planner presence, tool availability).
            deps: Optional runtime dependencies (e.g., file handles, clients).
            transport: Optional transport channel for streaming outputs.
                Kept separate from Task so Task remains serializable for
                audit and logging purposes.

        Returns:
            RunResult containing success status, output, errors, and metadata.

        Note:
            The execution mode is determined internally by the agent:
            - If agent has a planner OR task has milestones → Five-Layer Mode
            - If agent has tools but no planner → ReAct Mode
            - Otherwise → Simple Mode
        """

        ...


__all__ = ["IAgent"]
