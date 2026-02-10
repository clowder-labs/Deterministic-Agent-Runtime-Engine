from __future__ import annotations

from typing import Any

import pytest

from dare_framework.tool.tool_manager import ToolManager
from dare_framework.tool.types import CapabilityKind, ToolType
from dare_framework.infra.component import ComponentType


class DummyTool:
    def __init__(self, name: str, description: str) -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"text": {"type": "string"}}}

    @property
    def output_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"text": {"type": "string"}}}

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
        return "non_idempotent_effect"

    @property
    def requires_approval(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 12

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(self, input: dict[str, Any], context: Any) -> Any:
        return {"ok": True, "text": input.get("text")}


class ListProvider:
    def __init__(self, tools: list[DummyTool]) -> None:
        self._tools = tools

    def list_tools(self) -> list[DummyTool]:
        return list(self._tools)


@pytest.mark.asyncio
async def test_tool_manager_register_update_unregister() -> None:
    manager = ToolManager()
    tool = DummyTool("echo", "Echo input text")

    descriptor = manager.register_tool(tool)
    assert descriptor.id == "echo"

    manager.change_capability_status(descriptor.id, False)
    assert manager.list_capabilities() == []
    assert manager.list_capabilities(include_disabled=True)

    updated = DummyTool("echo", "Echo input payload")
    updated_descriptor = manager.update_tool(
        updated,
        capability_id=descriptor.id,
        enabled=True,
    )
    assert updated_descriptor.description == "Echo input payload"

    assert manager.unregister_tool(descriptor.id) is True
    assert manager.get_capability(descriptor.id, include_disabled=True) is None


@pytest.mark.asyncio
async def test_tool_manager_provider_registration() -> None:
    manager = ToolManager()
    provider = ListProvider([DummyTool("alpha", "A"), DummyTool("beta", "B")])

    manager.register_provider(provider)
    await manager.refresh()

    capabilities = manager.list_capabilities()
    assert len(capabilities) == 2

    assert manager.unregister_provider(provider) is True
    assert manager.list_capabilities() == []


def test_tool_manager_rejects_duplicate_tool_name() -> None:
    manager = ToolManager()
    manager.register_tool(DummyTool("echo", "Echo input text"))

    with pytest.raises(ValueError) as excinfo:
        manager.register_tool(DummyTool("echo", "Duplicate echo"))

    assert "echo" in str(excinfo.value)
