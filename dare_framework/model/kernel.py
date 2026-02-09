"""model domain stable interfaces."""

from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Literal

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse


class IModelAdapter(IComponent, ABC):
    """[Component] Model adapter contract for LLM invocation.

    Usage: Called by the agent to generate model responses.
    """

    @property
    def component_type(self) -> Literal[ComponentType.MODEL_ADAPTER]:
        return ComponentType.MODEL_ADAPTER

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the model adapter.
        """
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """
        Returns the name of the model.
        """
        ...

    @abstractmethod
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
