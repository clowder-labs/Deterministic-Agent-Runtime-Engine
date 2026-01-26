"""Model domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework.model.types import GenerateOptions, ModelResponse, Prompt

from dare_framework.config.types import Config
from dare_framework.infra.component import ComponentType, IComponent


@runtime_checkable
class IModelAdapter(IComponent, Protocol):
    """[Component] Model adapter contract for LLM invocation.

    Usage: Called by the agent to generate model responses.
    """

    @property
    def component_type(self) -> Literal[ComponentType.MODEL_ADAPTER]:
        ...

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

    def load_model_adapter(self, *, config: Config | None = None) -> IModelAdapter | None: ...


__all__ = ["IModelAdapter", "IModelAdapterManager"]
