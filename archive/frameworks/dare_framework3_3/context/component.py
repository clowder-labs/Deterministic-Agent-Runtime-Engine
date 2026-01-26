"""Context domain component interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework3_3.context.types import (
    AssembledContext,
    AssemblyRequest,
    Message,
    Prompt,
    RetrievalRequest,
)


class IContextStrategy(Protocol):
    """[Component] Strategy for building prompts from assembled context.

    Usage: Injected into the agent to customize prompt construction.
    """

    async def build_prompt(self, assembled: AssembledContext) -> Prompt:
        """[Component] Build the final prompt representation.

        Usage: Called after context assembly to prepare model input.
        """
        ...


@runtime_checkable
class IRetrievalContext(Protocol):
    """[Component] Uniform retrieval surface (Context Engineering Layer 2).

    Usage:
        Implemented by STM/LTM/knowledge sources. All retrieval outputs are
        returned as canonical `Message` objects with source attribution in
        metadata (e.g., `metadata["source"]`).

    Notes:
        - `get/recall/retrieve` are semantic aliases; implementations MAY
          implement only `get()` by inheriting `RetrievalContextAliases`.
    """

    async def get(self, req: RetrievalRequest) -> list[Message]:
        """[Component] Return messages relevant to the request query."""
        ...

    async def recall(self, req: RetrievalRequest) -> list[Message]:
        """[Component] Semantic alias of get()."""
        ...

    async def retrieve(self, req: RetrievalRequest) -> list[Message]:
        """[Component] Semantic alias of get()."""
        ...


class RetrievalContextAliases:
    """[Component] Convenience mixin implementing recall/retrieve as get().

    This mixin intentionally does not define get(); subclasses must implement it.
    """

    async def recall(self, req: RetrievalRequest) -> list[Message]:
        return await self.get(req)  # type: ignore[attr-defined]

    async def retrieve(self, req: RetrievalRequest) -> list[Message]:
        return await self.get(req)  # type: ignore[attr-defined]


@runtime_checkable
class IAssemblyContext(Protocol):
    """[Component] Session-scoped context assembly surface (Context Engineering Layer 3).

    Usage:
        Held by SessionContext as `session.assembly`. Callers use
        `await session.assembly.assemble(req)` to get a `list[Message]`
        that can be sent directly to the LLM.

    Notes:
        - Tools MUST be injected as messages (typically a system tool-catalog message).
        - Budget enforcement/compaction is applied during assembly.
    """

    async def assemble(self, req: AssemblyRequest) -> list[Message]:
        """[Component] Assemble a message list for the request."""
        ...


# Backwards-compatible alias for older naming.
IContextAssembler = IAssemblyContext


__all__ = [
    "IContextStrategy",
    "IRetrievalContext",
    "RetrievalContextAliases",
    "IAssemblyContext",
    "IContextAssembler",
]
