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

    async def invoke(
            self,
            action: ResourceAction,
            _params: dict[str, Any],
    ) -> Any:
        if action != ResourceAction.MODEL_GET:
            raise ValueError(f"unsupported model action: {action.value}")
        return dict(self._manager.current())


__all__ = ["IModelInfoManager", "ModelActionHandler"]
