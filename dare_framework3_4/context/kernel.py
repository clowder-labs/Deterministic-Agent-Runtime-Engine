"""context domain stable interfaces.

This domain defines the v3.4 "context-centric" contract used as v4.0 evidence:
- Retrieval references live on Context (STM/LTM/Knowledge).
- `assemble()` constructs request-time (messages + tools + metadata).
"""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework3_4.context.types import AssembledContext, Budget, Message


class IRetrievalContext(Protocol):
    """Unified retrieval interface implemented by memory/knowledge."""

    def get(self, query: str = "", **kwargs: Any) -> list[Message]: ...


class IContext(Protocol):
    """Context interface - core context entity (context-centric)."""

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

    # Tool listing (for Prompt.tools)
    def listing_tools(self) -> list[dict[str, Any]]: ...

    # Assembly (core)
    def assemble(self, **options: Any) -> AssembledContext: ...

    # Config
    def config_update(self, patch: dict[str, Any]) -> None: ...


__all__ = ["IContext", "IRetrievalContext"]

