"""agent domain stable interfaces.

Alignment note:
- The minimal runtime surface is `IAgent.__call__(...)` (orchestration is an agent concern).

Design Decision (2026-01-30):
    The `IAgent.__call__()` method accepts both `str` and `Task` for flexibility:
    
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

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from dare_framework.agent.status import AgentStatus
from dare_framework.plan.types import RunResult, Task

if TYPE_CHECKING:
    from dare_framework.transport.kernel import AgentChannel


class IAgent(ABC):
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
        result = await agent("Explain this codebase")

        # Task object for advanced control
        task = Task(
            description="Implement feature X",
            milestones=[
                Milestone(milestone_id="m1", description="Design API"),
                Milestone(milestone_id="m2", description="Write tests"),
            ],
        )
        result = await agent(task)
    """

    @abstractmethod
    async def __call__(
        self,
        message: str | Task,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Invoke the agent directly.

        If no transport is provided, implementations may route through a no-op
        transport to keep the execution pipeline consistent.
        """
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        """Start agent components and spawn the transport loop if configured."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """Stop agent components and cancel the transport loop."""
        raise NotImplementedError

    @abstractmethod
    def interrupt(self) -> None:
        """Interrupt current in-flight execution if supported."""
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> dict[str, Any]:
        """Pause execution if supported by the concrete agent."""
        raise NotImplementedError

    @abstractmethod
    def retry(self) -> dict[str, Any]:
        """Retry the last execution step if supported."""
        raise NotImplementedError

    @abstractmethod
    def reverse(self) -> dict[str, Any]:
        """Rollback/reverse execution if supported."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> AgentStatus:
        """Return current lifecycle status."""
        raise NotImplementedError


__all__ = ["IAgent"]
