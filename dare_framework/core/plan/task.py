from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dare_framework.contracts.ids import generator_id


@dataclass
class Milestone:
    """A single closed-loop objective within a task (v2.0)."""

    milestone_id: str
    description: str
    user_input: str
    order: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A high-level execution request (v2.0)."""

    description: str
    task_id: str = field(default_factory=lambda: generator_id("task"))
    context: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    milestones: list[Milestone] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_milestones(self) -> list[Milestone]:
        """Derive milestones from the task when none are provided."""

        if self.milestones is not None:
            return self.milestones
        return [
            Milestone(
                milestone_id=generator_id("milestone"),
                description=self.description,
                user_input=self.description,
                order=0,
            )
        ]
