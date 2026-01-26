"""Model domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework.model.types import GenerateOptions, ModelResponse, Prompt


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

class IModelAdapterManager(Protocol):
    """Loads the model adapter implementation (single-select)."""

    def load_model_adapter(self, *, config: Any | None = None) -> object | None: ...


__all__ = ["IModelAdapter", "IModelAdapterManager"]
