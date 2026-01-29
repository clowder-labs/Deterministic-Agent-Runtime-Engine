"""model domain stable interfaces."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse


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
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        """[Component] Generate a model response for a model input.

        Usage: Called during plan or execution stages.
        """
        ...


__all__ = ["IModelAdapter"]
