"""Run context state for bridging agent state to tool contexts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework3_4.tool.types import RunContext


@dataclass
class RunContextState:
    """Bridges agent execution state into tool execution contexts."""

    deps: Any | None = None
    run_id: str = ""
    task_id: str | None = None
    milestone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    config: Any | None = None

    def build(self) -> RunContext[Any]:
        """Build a RunContext from the current state."""
        return RunContext(
            deps=self.deps,
            run_id=self.run_id,
            task_id=self.task_id,
            milestone_id=self.milestone_id,
            metadata=dict(self.metadata),
            config=self.config,
        )
