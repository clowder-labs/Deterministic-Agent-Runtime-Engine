"""agent domain pluggable interfaces.

This module contains optional strategy interfaces that are not treated as Kernel
contracts (e.g., orchestration strategies).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from dare_framework.context import Message
from dare_framework.plan.types import RunResult

if TYPE_CHECKING:
    from dare_framework.transport.kernel import AgentChannel


class IAgentOrchestration(ABC):
    """A pluggable orchestration strategy (five-layer loop is only one option)."""

    @abstractmethod
    async def execute(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute one orchestration task."""
        raise NotImplementedError


__all__ = ["IAgentOrchestration"]
