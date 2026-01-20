"""Context domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResourceType(Enum):
    """Canonical resource types for budget accounting."""

    TOKENS = "tokens"
    COST = "cost"
    TIME_SECONDS = "time_seconds"
    TOOL_CALLS = "tool_calls"


@dataclass(frozen=True)
class Budget:
    """Coarse-grained budgets for a scope or envelope."""

    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None


class ResourceExhausted(RuntimeError):
    """Raised when a budget limit is exceeded."""


@dataclass(frozen=True)
class Message:
    """Canonical message representation."""

    role: str
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextStage(Enum):
    """Context assembly stages aligned to the five-layer loop."""

    SESSION_OBSERVE = "session_observe"
    MILESTONE_OBSERVE = "milestone_observe"
    PLAN = "plan"
    EXECUTE = "execute"
    TOOL = "tool"
    VERIFY = "verify"


@dataclass(frozen=True)
class Context:
    """The assembled context window input with attribution metadata."""

    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)


# Legacy alias for callers still using the old name.
AssembledContext = Context


@dataclass(frozen=True)
class Prompt:
    """A final prompt representation for model adapters."""

    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedContext:
    """Retrieval output for context assembly."""

    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class IndexStatus:
    """Index readiness status for a scope."""

    ready: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextPacket:
    """Cross-window / cross-agent context handoff packet."""

    id: str
    source: str
    target: str
    summary: str
    attachments: list[str] = field(default_factory=list)
    budget_attribution: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeStateView:
    """Minimal state view for context assembly."""

    task_id: str
    run_id: str
    milestone_id: str | None
    stage: ContextStage
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """A session-scoped context holder."""

    user_input: str
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "ResourceType",
    "Budget",
    "ResourceExhausted",
    "Message",
    "ContextStage",
    "Context",
    "AssembledContext",
    "Prompt",
    "RetrievedContext",
    "IndexStatus",
    "ContextPacket",
    "RuntimeStateView",
    "SessionContext",
]
