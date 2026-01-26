"""Default BaseAgent implementation (interface-aligned)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dare_framework.plan.types import RunResult, Task


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

__all__ = ["BaseAgent"]
