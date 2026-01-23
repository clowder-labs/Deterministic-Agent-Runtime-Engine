"""agent domain stable interfaces.

v4.0 alignment note:
- The minimal runtime surface is `IAgent.run(...)` (orchestration is an agent concern).
"""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework3_4.plan.types import RunResult, Task


class IAgent(Protocol):
    """Framework minimal runtime surface."""

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        """Execute `task` and return a structured RunResult.

        `deps` is intentionally separate from `Task` so `Task` remains serializable
        for audit/logging (alignment with v4.0 docs).
        """

        ...

__all__ = ["IAgent"]
