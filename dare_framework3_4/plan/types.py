"""Plan domain types - Task and RunResult for agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Task:
    """A high-level execution request.

    Represents the top-level goal provided by the user.

    Attributes:
        description: The task description
        task_id: Unique identifier (auto-generated if not provided)
        context: Additional context data
        constraints: Execution constraints
        created_at: Task creation timestamp
    """

    description: str
    task_id: str = field(default_factory=lambda: f"task_{datetime.now(timezone.utc).timestamp()}")
    context: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SessionSummary:
    """Summary of a session execution.

    Attributes:
        session_id: Session identifier
        milestone_count: Number of milestones
        success: Whether the session succeeded
        completed_at: Completion timestamp
    """

    session_id: str
    milestone_count: int
    success: bool
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class MilestoneResult:
    """Complete result of a milestone execution.

    Attributes:
        success: Whether the milestone succeeded
        outputs: Tool outputs
        errors: Error messages
    """

    success: bool
    outputs: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RunResult:
    """Top-level execution result returned to developers.

    Attributes:
        success: Whether the run succeeded
        output: Final output (from last milestone)
        milestone_results: Results for each milestone
        errors: Error messages
        session_summary: Session summary
    """

    success: bool
    output: Any | None = None
    milestone_results: list[MilestoneResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    session_summary: SessionSummary | None = None


__all__ = ["Task", "RunResult", "SessionSummary", "MilestoneResult"]
