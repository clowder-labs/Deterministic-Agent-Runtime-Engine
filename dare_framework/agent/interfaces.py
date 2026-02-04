"""agent domain pluggable interfaces.

This module contains optional strategy interfaces that are not treated as Kernel
contracts (e.g., orchestration strategies).
"""

from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING, runtime_checkable

from dare_framework.plan.types import RunResult, Task

if TYPE_CHECKING:
    from dare_framework.transport.kernel import AgentChannel


@runtime_checkable
class IAgentOrchestration(Protocol):
    """A pluggable orchestration strategy (five-layer loop is only one option)."""

    async def run_task(
        self,
        task: Task,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult: ...


__all__ = ["IAgentOrchestration"]
