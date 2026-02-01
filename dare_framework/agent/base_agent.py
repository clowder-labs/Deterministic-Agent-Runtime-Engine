"""Default BaseAgent implementation (interface-aligned)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from dare_framework.plan.types import RunResult, Task

if TYPE_CHECKING:
    from dare_framework.agent._internal.builder import DareAgentBuilder, ReactAgentBuilder, SimpleChatAgentBuilder
    from dare_framework.skill.types import Skill


class BaseAgent(ABC):
    """Abstract base class for all agent implementations.

    Provides common interface for agent execution.
    """

    def __init__(self, name: str) -> None:
        """Initialize base agent.

        Args:
            name: Agent name identifier.
        """
        self._name = name

    @property
    def name(self) -> str:
        """Agent name."""
        return self._name

    def set_skill(self, skill: "Skill | None") -> None:
        """Mount or replace current skill. None clears. Delegates to context."""
        ctx = getattr(self, "_context", None)
        if ctx is not None and hasattr(ctx, "set_skill"):
            ctx.set_skill(skill)

    def clear_skill(self) -> None:
        """Unmount current skill. Delegates to context."""
        ctx = getattr(self, "_context", None)
        if ctx is not None and hasattr(ctx, "clear_skill"):
            ctx.clear_skill()

    def current_skill(self) -> "Skill | None":
        """Get current skill, if any. Delegates to context."""
        ctx = getattr(self, "_context", None)
        if ctx is not None and hasattr(ctx, "current_skill"):
            return ctx.current_skill()
        return None

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        """Run a task and return a structured RunResult.

        Args:
            task: Task description or Task object.
            deps: Optional dependencies (currently unused).

        Returns:
            RunResult with output content.
        """
        task_description = task.description if isinstance(task, Task) else task
        output = await self._execute(task_description)
        return RunResult(success=True, output=output)

    @abstractmethod
    async def _execute(self, task: str) -> str:
        """Execute task - must be implemented by subclasses.

        Args:
            task: Task description to execute.

        Returns:
            Model response as string.
        """
        ...

    @staticmethod
    def simple_chat_agent_builder(name: str) -> SimpleChatAgentBuilder:
        """Return a builder for SimpleChatAgent."""
        from dare_framework.agent._internal.builder import SimpleChatAgentBuilder

        return SimpleChatAgentBuilder(name)

    @staticmethod
    def react_agent_builder(name: str) -> ReactAgentBuilder:
        """Return a builder for ReactAgent (ReAct tool loop)."""
        from dare_framework.agent._internal.builder import ReactAgentBuilder

        return ReactAgentBuilder(name)

    @staticmethod
    def five_layer_agent_builder(name: str) -> DareAgentBuilder:
        """Return a builder for DareAgent (five-layer orchestration)."""
        from dare_framework.agent._internal.builder import DareAgentBuilder

        return DareAgentBuilder(name)


__all__ = ["BaseAgent"]
