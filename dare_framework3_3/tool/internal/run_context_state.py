"""Run context state for bridging agent state to tool contexts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework3_3.tool.types import RunContext


@dataclass
class RunContextState:
    """Bridges agent execution state into tool execution contexts.
    
    Maintains state that gets passed to tools during execution.
    
    Attributes:
        deps: User-provided dependencies
        run_id: Current run identifier
        task_id: Current task identifier
        milestone_id: Current milestone identifier
        metadata: Additional context data
    """
    deps: Any | None = None
    run_id: str = ""
    task_id: str | None = None
    milestone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def build(self) -> RunContext[Any]:
        """Build a RunContext from the current state."""
        return RunContext(
            deps=self.deps,
            run_id=self.run_id,
            task_id=self.task_id,
            milestone_id=self.milestone_id,
            metadata=dict(self.metadata),
        )
