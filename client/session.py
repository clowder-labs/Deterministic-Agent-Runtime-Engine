"""Session and shell state models for the CLI runtime."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class ExecutionMode(Enum):
    """Top-level execution mode for user-entered tasks."""

    PLAN = "plan"
    EXECUTE = "execute"


class SessionStatus(Enum):
    """Interactive session state."""

    IDLE = "idle"
    AWAITING_APPROVAL = "awaiting"
    RUNNING = "running"


@dataclass
class CLISessionState:
    """Mutable state shared by interactive command handlers."""

    mode: ExecutionMode = ExecutionMode.EXECUTE
    status: SessionStatus = SessionStatus.IDLE
    pending_plan: Any | None = None
    pending_task_description: str | None = None
    active_execution_task: asyncio.Task[Any] | None = None
    active_execution_description: str | None = None
    conversation_id: str = field(default_factory=lambda: uuid4().hex)
    execution_failures: int = 0
    last_execution_success: bool | None = None
    pending_runtime_approvals: set[str] = field(default_factory=set)
    headless_failure_payload: dict[str, Any] | None = None

    def clear_pending(self) -> None:
        """Drop in-memory plan preview state."""
        self.pending_plan = None
        self.pending_task_description = None

    def mark_runtime_approval_pending(self, request_id: str) -> None:
        """Track a transport approval that needs user action."""
        normalized = request_id.strip() or "?"
        self.pending_runtime_approvals.add(normalized)

    def mark_runtime_approval_resolved(self, request_id: str) -> None:
        """Clear a tracked runtime approval once transport reports resolution."""
        normalized = request_id.strip() or "?"
        if normalized == "?":
            self.pending_runtime_approvals.clear()
            return
        self.pending_runtime_approvals.discard(normalized)

    def has_pending_runtime_approval(self) -> bool:
        """Return True when the running task is blocked on user approval."""
        return bool(self.pending_runtime_approvals)

    def clear_runtime_approvals(self) -> None:
        """Clear approval state when execution ends or resets."""
        self.pending_runtime_approvals.clear()
