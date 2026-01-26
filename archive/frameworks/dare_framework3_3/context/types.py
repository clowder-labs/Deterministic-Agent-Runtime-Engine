"""[Types] Context domain data types and context assembly models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dare_framework3_3.config.types import Config
    from dare_framework3_3.context.component import IAssemblyContext


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
    """Canonical message representation.

    Notes:
        - tool_calls/tool_call_id are optional fields used by model adapters
          that support tool calling (e.g., OpenAI-compatible adapters).
        - Tools available to the model should be described via system messages
          during context assembly (Context Engineering Layer 3).
    """

    role: str
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
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
class RetrievalRequest:
    """Request envelope for retrieval (Context Engineering Layer 2).

    Retrieval sources (STM/LTM/knowledge) all accept the same request shape.
    Implementations should treat limits as best-effort; hard enforcement
    happens during context assembly under the final budget.
    """

    query: str
    stage: "ContextStage | None" = None
    state: "RuntimeStateView | None" = None
    budget: Budget | None = None
    top_k: int | None = None
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssemblyRequest:
    """Request envelope for context assembly (Context Engineering Layer 3).

    Assembly is responsible for:
    - Injecting tool catalogs/usage guidance as messages
    - Merging retrieval outputs into a single message sequence
    - Applying compaction/truncation to satisfy the budget
    """

    stage: ContextStage
    state: RuntimeStateView
    query: str | None = None
    budget: Budget | None = None


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
    """A session-scoped context holder.

    Notes:
        SessionContext holds the session-scoped AssemblyContext as `assembly`.
        Callers should use `await session.assembly.assemble(AssemblyRequest(...))`
        to obtain a `list[Message]` that can be sent directly to the LLM.
    """

    user_input: str
    metadata: dict[str, Any] = field(default_factory=dict)
    # Effective config snapshot for the session lifecycle (resolved by ConfigProvider at session start).
    # Keep this off the message path; it is runtime-internal and may contain secrets (e.g., API keys).
    config: "Config | None" = None
    assembly: "IAssemblyContext | None" = None


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
    "RetrievalRequest",
    "AssemblyRequest",
    "IndexStatus",
    "ContextPacket",
    "RuntimeStateView",
    "SessionContext",
]
