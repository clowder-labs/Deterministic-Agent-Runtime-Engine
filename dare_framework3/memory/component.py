"""Memory domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework3.context.types import Budget


@runtime_checkable
class IMemory(Protocol):
    """Memory interface for retrieval and persistence."""

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
class IPromptStore(Protocol):
    """Prompt template storage interface."""

    async def get(self, prompt_id: str) -> str | None:
        ...

    async def set(self, prompt_id: str, content: str) -> None:
        ...


__all__ = ["IMemory", "IPromptStore"]
