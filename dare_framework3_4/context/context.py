"""Context domain - v3.4.1 architecture.

This module defines:
- IRetrievalContext: Unified retrieval interface (inherited by memory/knowledge)
- IContext: Context interface
- Context: Context implementation
- Types: Message, Budget, AssembledContext
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol
import uuid

if TYPE_CHECKING:
    from dare_framework3_4.tool.component import IToolProvider


# ============================================================
# Types
# ============================================================

@dataclass
class Message:
    """Unified message format.

    Attributes:
        role: Message role (system / user / assistant / tool).
        content: Message content.
        name: Tool name (used when role=tool).
        metadata: Extension fields for tracing, attribution, etc.
    """

    role: str
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Budget:
    """Resource budget = limits + usage tracking.

    Attributes:
        max_*: Resource limits (None means unlimited).
        used_*: Current usage counters.
    """

    # Limits
    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None

    # Usage tracking
    used_tokens: float = 0.0
    used_cost: float = 0.0
    used_time_seconds: float = 0.0
    used_tool_calls: int = 0


@dataclass
class AssembledContext:
    """Request-time context for a single LLM call.

    Constructed by Context.assemble() before each LLM invocation.

    Attributes:
        messages: Message sequence to send to the model.
        tools: Tool definitions (provided by IToolProvider).
        metadata: Debug info, attribution, budget consumption notes.
    """

    messages: list[Message]
    tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Interfaces
# ============================================================

class IRetrievalContext(Protocol):
    """Unified retrieval interface.

    Inherited by IShortTermMemory, ILongTermMemory, IKnowledge.
    All memory/knowledge implementations must implement this interface.
    """

    def get(self, query: str = "", **kwargs) -> list[Message]:
        """Retrieve relevant messages based on query."""
        ...


class IContext(Protocol):
    """Context interface - core context entity.

    As defined in v3.4.1 architecture.
    Messages are not stored as a field, but assembled on-demand.
    """

    # Fields
    id: str
    short_term_memory: IRetrievalContext
    budget: Budget
    long_term_memory: IRetrievalContext | None
    knowledge: IRetrievalContext | None
    toollist: list[dict[str, Any]] | None
    config: dict[str, Any] | None

    # Short-term memory methods
    def stm_add(self, message: Message) -> None: ...
    def stm_get(self) -> list[Message]: ...
    def stm_clear(self) -> list[Message]: ...

    # Budget methods
    def budget_use(self, resource: str, amount: float) -> None: ...
    def budget_check(self) -> None: ...
    def budget_remaining(self, resource: str) -> float: ...

    # Tool methods
    def listing_tools(self) -> list[dict[str, Any]]: ...

    # Assembly methods
    def assemble(self, **options) -> AssembledContext: ...

    # Config methods
    def config_update(self, patch: dict[str, Any]) -> None: ...


# ============================================================
# Implementation
# ============================================================

@dataclass
class Context(IContext):
    """v3.4.1 Context implementation.

    Messages are NOT stored as a field, but assembled on-demand via assemble().

    Fields (as per architecture):
        id: Unique context identifier
        short_term_memory: IRetrievalContext (current session)
        budget: Resource limits and usage
        long_term_memory: IRetrievalContext | None (external)
        knowledge: IRetrievalContext | None (external)
        toollist: Cached tool list | None
        config: Dynamic configuration | None
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    budget: Budget = field(default_factory=Budget)
    config: dict[str, Any] | None = None

    # IRetrievalContext references
    short_term_memory: IRetrievalContext | None = None
    long_term_memory: IRetrievalContext | None = None
    knowledge: IRetrievalContext | None = None

    # Tool provider (internal, for listing_tools)
    _tool_provider: "IToolProvider | None" = field(default=None, repr=False)

    # Cached tool list
    toollist: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        """Initialize default short-term memory if not provided."""
        if self.short_term_memory is None:
            from dare_framework3_4.memory.internal.in_memory_stm import InMemorySTM
            self.short_term_memory = InMemorySTM()

    # ========== Short-term Memory Methods ==========

    def stm_add(self, message: Message) -> None:
        """Add a message to short-term memory."""
        self.short_term_memory.add(message)  # type: ignore

    def stm_get(self) -> list[Message]:
        """Get all messages from short-term memory."""
        return self.short_term_memory.get()

    def stm_clear(self) -> list[Message]:
        """Clear short-term memory, returns empty list."""
        self.short_term_memory.clear()  # type: ignore
        return []

    # ========== Budget Methods ==========

    def budget_use(self, resource: str, amount: float) -> None:
        """Record resource consumption."""
        if resource == "tokens":
            self.budget.used_tokens += amount
        elif resource == "cost":
            self.budget.used_cost += amount
        elif resource == "time_seconds":
            self.budget.used_time_seconds += amount
        elif resource == "tool_calls":
            self.budget.used_tool_calls += int(amount)

    def budget_check(self) -> None:
        """Check if any budget limit is exceeded."""
        b = self.budget
        if b.max_tokens is not None and b.used_tokens > b.max_tokens:
            raise RuntimeError(
                f"Token budget exceeded: {b.used_tokens}/{b.max_tokens}"
            )
        if b.max_cost is not None and b.used_cost > b.max_cost:
            raise RuntimeError(
                f"Cost budget exceeded: {b.used_cost}/{b.max_cost}"
            )
        if b.max_tool_calls is not None and b.used_tool_calls > b.max_tool_calls:
            raise RuntimeError(
                f"Tool call budget exceeded: {b.used_tool_calls}/{b.max_tool_calls}"
            )
        if b.max_time_seconds is not None and b.used_time_seconds > b.max_time_seconds:
            raise RuntimeError(
                f"Time budget exceeded: {b.used_time_seconds}/{b.max_time_seconds}"
            )

    def budget_remaining(self, resource: str) -> float:
        """Get remaining budget for a resource."""
        b = self.budget
        if resource == "tokens":
            return (b.max_tokens - b.used_tokens) if b.max_tokens else float("inf")
        elif resource == "cost":
            return (b.max_cost - b.used_cost) if b.max_cost else float("inf")
        elif resource == "tool_calls":
            return (b.max_tool_calls - b.used_tool_calls) if b.max_tool_calls else float("inf")
        elif resource == "time_seconds":
            return (b.max_time_seconds - b.used_time_seconds) if b.max_time_seconds else float("inf")
        return float("inf")

    # ========== Tool Methods ==========

    def listing_tools(self) -> list[dict[str, Any]]:
        """Get tool list (internally calls IToolProvider)."""
        if self._tool_provider is not None:
            self.toollist = self._tool_provider.list_tools()
        return self.toollist or []

    # ========== Assembly Methods (Core) ==========

    def assemble(self, **options) -> AssembledContext:
        """Assemble context for LLM call. Can be overridden by subclasses."""
        messages = self.stm_get()
        tools = self.listing_tools()
        return AssembledContext(
            messages=messages,
            tools=tools,
            metadata={"context_id": self.id},
        )

    # ========== Config Methods ==========

    def config_update(self, patch: dict[str, Any]) -> None:
        """Update context configuration (incremental merge)."""
        if self.config is None:
            self.config = {}
        self.config.update(patch)


__all__ = [
    # Types
    "Message",
    "Budget",
    "AssembledContext",
    # Interfaces
    "IRetrievalContext",
    "IContext",
    # Implementation
    "Context",
]
