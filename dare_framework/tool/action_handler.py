"""Tool-domain deterministic action handlers."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.tool import IToolManager
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler


class IToolCatalog(Protocol):
    """Minimal tool catalog contract required by interaction actions."""

    def list_capabilities(self) -> list[Any]:
        """Return registered capability descriptors."""


class ToolsActionHandler(IActionHandler):
    """Handle deterministic tool-domain actions."""

    def __init__(self, tool_manager: IToolManager) -> None:
        self._tool_manager = tool_manager

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.TOOLS_LIST}

    async def invoke(
        self,
        action: ResourceAction,
        _params: dict[str, Any],
    ) -> Any:
        if action != ResourceAction.TOOLS_LIST:
            raise ValueError(f"unsupported tools action: {action.value}")
        tools = []
        for cap in self._tool_manager.list_capabilities():
            tools.append(_capability_to_dict(cap))
        return {"tools": tools}


def _capability_to_dict(cap: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("id", "type", "name", "description", "input_schema", "output_schema", "metadata"):
        if hasattr(cap, key):
            val = getattr(cap, key)
            out[key] = val.value if hasattr(val, "value") else val
    return out


__all__ = ["IToolCatalog", "ToolsActionHandler"]
