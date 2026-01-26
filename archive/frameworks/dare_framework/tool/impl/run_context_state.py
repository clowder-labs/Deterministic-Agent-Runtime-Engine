from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework.contracts.run_context import RunContext
from dare_framework.config import Config


@dataclass
class RunContextState:
    """Bridges the Kernel v2 runtime into v1-style tool execution contexts (MVP)."""

    deps: Any | None = None
    run_id: str = ""
    task_id: str | None = None
    milestone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    config: Config | None = None

    def build(self) -> RunContext:
        return RunContext(
            deps=self.deps,
            run_id=self.run_id,
            task_id=self.task_id,
            milestone_id=self.milestone_id,
            metadata=dict(self.metadata),
            config=self.config,
        )
