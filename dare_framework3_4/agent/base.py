"""BaseAgent - abstract base class for agent implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dare_framework3_4.plan import Task, RunResult


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
        """Run a task and return the result.

        Args:
            task: Task description (string) or Task object.
            deps: Optional dependencies (unused in v3.4, kept for compatibility).

        Returns:
            RunResult with execution outcome.
        """
        task_obj = task if isinstance(task, Task) else Task(description=task)
        return await self._execute(task_obj)

    @abstractmethod
    async def _execute(self, task: Task) -> RunResult:
        """Execute task - must be implemented by subclasses.

        Args:
            task: Task to execute.

        Returns:
            RunResult with execution outcome.
        """
        ...


__all__ = ["BaseAgent"]
