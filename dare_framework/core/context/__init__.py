from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from dare_framework.contracts.model import Message
from dare_framework.core.budget import Budget


class ContextStage(Enum):
    """Context assembly stages aligned to the five-layer loop (v2.0)."""

    SESSION_OBSERVE = "session_observe"
    MILESTONE_OBSERVE = "milestone_observe"
    PLAN = "plan"
    EXECUTE = "execute"
    TOOL = "tool"
    VERIFY = "verify"


@dataclass(frozen=True)
class AssembledContext:
    """The assembled context window input, plus optional attribution metadata."""

    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Prompt:
    """A final prompt representation for model adapters (v2.0)."""

    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedContext:
    """Retrieval output for context assembly (may be empty in MVP)."""

    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class IndexStatus:
    """Index readiness status for a scope (may be a no-op in MVP)."""

    ready: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextPacket:
    """Cross-window / cross-agent context handoff packet (optional in MVP)."""

    id: str
    source: str
    target: str
    summary: str
    attachments: list[str] = field(default_factory=list)
    budget_attribution: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeStateView:
    """Minimal state view used by the context manager to assemble prompts (v2.0)."""

    task_id: str
    run_id: str
    milestone_id: str | None
    stage: ContextStage
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """A session-scoped context holder returned by IContextManager.open_session()."""

    user_input: str
    metadata: dict[str, Any] = field(default_factory=dict)


class IContextManager(Protocol):
    """Context engineering responsibility owner (v2.0)."""

    def open_session(self, task: "Task") -> SessionContext: ...

    async def assemble(self, stage: ContextStage, state: RuntimeStateView) -> AssembledContext: ...

    async def retrieve(self, query: str, *, budget: Budget) -> RetrievedContext: ...

    async def ensure_index(self, scope: str) -> IndexStatus: ...

    async def compress(self, context: AssembledContext, *, budget: Budget) -> AssembledContext: ...

    async def route(self, packet: ContextPacket, target: str) -> None: ...
