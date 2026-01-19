from __future__ import annotations

from dare_framework.components.base_component import ConfigurableComponent
from dare_framework.components.plugin_system.component_type import ComponentType

from .protocols import IPromptStore


class NoOpPromptStore(ConfigurableComponent, IPromptStore):
    """A prompt store that returns no templates (MVP placeholder)."""

    component_type = ComponentType.PROMPT_STORE
    name = "noop"

    async def get(self, prompt_id: str) -> str | None:
        return None

