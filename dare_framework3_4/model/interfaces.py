"""Model domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework3_4.model.types import GenerateOptions, ModelResponse, Prompt


@runtime_checkable
class IModelAdapter(Protocol):
    """[Component] Model adapter contract for LLM invocation.

    Usage: Called by the agent to generate model responses.
    """

    async def generate(
        self,
        prompt: "Prompt",
        *,
        options: "GenerateOptions | None" = None,
    ) -> "ModelResponse":
        """[Component] Generate a model response for a prompt.

        Usage: Called during plan or execution stages.
        """
        ...


__all__ = ["IModelAdapter"]
