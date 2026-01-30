"""agent domain stable interfaces.

Alignment note:
- The minimal runtime surface is `IAgent.run(...)` (orchestration is an agent concern).
"""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.plan.types import RunResult, Task

# TODO(@zts): Consider simplifying IAgent.run() signature.
# Current design accepts `str | Task`, but `Task` contains `milestones` which is
# an orchestration concept. For a minimal Kernel interface, consider:
# - IAgent.run(task: str) → simple string input
# - IAgentOrchestration.execute(task: Task) → full Task with milestones
# This would better separate Kernel (minimal) from Orchestration (rich).


class IAgent(Protocol):
    """Framework minimal runtime surface."""

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        """Execute `task` and return a structured RunResult.

        `deps` is intentionally separate from `Task` so `Task` remains serializable
        for audit/logging.
        """

        ...

__all__ = ["IAgent"]
