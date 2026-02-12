"""Model-domain deterministic action handlers."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.model import IModelAdapterManager
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler


class IModelInfoManager(Protocol):
    """Minimal model-info manager contract required by interaction actions."""

    def current(self) -> dict[str, Any]:
        """Return current model info snapshot."""


class ModelActionHandler(IActionHandler):
    """Handle deterministic model-domain actions."""

    def __init__(self, agent: BaseAgent, config: Config, model_manager: IModelAdapterManager) -> None:
        self._agent = agent
        self._config = config
        self._model_manager = model_manager

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.MODEL_GET}

    # noinspection PyMethodOverriding
    async def invoke(
            self,
            action: ResourceAction,
            **_params: Any,
    ) -> Any:
        if action == ResourceAction.MODEL_GET:
            return self._model_get()
        raise ValueError(f"unsupported model action: {action.value}")

    def _model_get(self) -> dict[str, Any]:
        model = getattr(self._agent, "_model", None)
        if model is None:
            model = self._model_manager.load_model_adapter(config=self._config)
        if model is None:
            return {"name": None, "model": None}
        return {
            "name": getattr(model, "name", None),
            "model": getattr(model, "model", None),
        }


__all__ = ["IModelInfoManager", "ModelActionHandler"]
