"""agent domain pluggable interfaces.

This module contains optional strategy interfaces that are not treated as Kernel
contracts (e.g., orchestration strategies).
"""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework3_4.plan.types import RunResult, Task


class IAgentOrchestration(Protocol):
    """A pluggable orchestration strategy (five-layer loop is only one option)."""

    async def execute(self, task: Task, deps: Any | None = None) -> RunResult: ...


__all__ = ["IAgentOrchestration"]

