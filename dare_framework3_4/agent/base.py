"""BaseAgent - abstract base class for agent implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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

    async def run(self, task: str, deps: Any | None = None) -> str:
        """Run a task and return the result.

        Args:
            task: Task description (string).
            deps: Optional dependencies (unused in v3.4, kept for compatibility).

        Returns:
            Model response as string.
        """
        return await self._execute(task)

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
