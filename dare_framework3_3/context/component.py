"""Context domain component interfaces."""

from __future__ import annotations

from typing import Protocol

from dare_framework3_3.context.types import AssembledContext, Prompt


class IContextStrategy(Protocol):
    """[Component] Strategy for building prompts from assembled context.

    Usage: Injected into the agent to customize prompt construction.
    """

    async def build_prompt(self, assembled: AssembledContext) -> Prompt:
        """[Component] Build the final prompt representation.

        Usage: Called after context assembly to prepare model input.
        """
        ...


__all__ = ["IContextStrategy"]
