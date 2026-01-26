"""Context domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from dare_framework.context.types import AssembledContext, IndexStatus, Prompt, RetrievedContext
from dare_framework.builder.plugin_system.configurable_component import IConfigurableComponent

if TYPE_CHECKING:
    from dare_framework.execution.types import Budget


@runtime_checkable
class IContextStrategy(Protocol):
    """Prompt/context assembly strategy interface (Layer 2)."""

    async def build_prompt(self, assembled: AssembledContext) -> Prompt: ...


@runtime_checkable
class IMemory(Protocol):
    """Memory interface for retrieval and persistence (Layer 2)."""

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget | None" = None,
    ) -> list[dict[str, Any]]:
        ...

    async def add(self, items: list[dict[str, Any]]) -> None:
        ...


@runtime_checkable
class IPromptStore(IConfigurableComponent, Protocol):
    """Prompt template storage interface (Layer 2)."""

    async def get(self, prompt_id: str) -> str | None: ...

    async def set(self, prompt_id: str, content: str) -> None: ...


class IRetriever(Protocol):
    """Retrieval component for context engineering."""

    async def retrieve(self, query: str, *, budget: "Budget | None" = None) -> RetrievedContext: ...


class IIndexer(Protocol):
    """Indexing component for retrieval readiness."""

    async def ensure_index(self, scope: str) -> IndexStatus: ...

    async def add(self, scope: str, items: list[dict]) -> None: ...


__all__ = [
    "IMemory",
    "IPromptStore",
    "IContextStrategy",
    "IRetriever",
    "IIndexer",
]
