from __future__ import annotations

from typing import Any

import pytest

from dare_framework.tool import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityType,
    ProviderStatus,
    ToolManager,
    ToolType,
)


class DummyTool:
    def __init__(self, name: str, description: str) -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

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


class FakeProvider:
    def __init__(self, capabilities: list[CapabilityDescriptor]) -> None:
        self._capabilities = capabilities

    async def list(self) -> list[CapabilityDescriptor]:
        return list(self._capabilities)

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        return {"capability_id": capability_id, **params}

    async def health_check(self) -> ProviderStatus:
        return ProviderStatus.HEALTHY


def test_tool_manager_register_update_unregister() -> None:
    manager = ToolManager()
    tool = DummyTool("echo", "Echo input text")

    descriptor = manager.register_tool(tool)
    assert descriptor.id == "tool:echo"

    manager.set_capability_enabled(descriptor.id, False)
    assert manager.list_tool_defs() == []
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
async def test_tool_manager_provider_aggregation() -> None:
    manager = ToolManager()

    capability_a = CapabilityDescriptor(
        id="tool:a",
        type=CapabilityType.TOOL,
        name="a",
        description="tool a",
        input_schema={"type": "object", "properties": {}},
    )
    capability_b = CapabilityDescriptor(
        id="tool:b",
        type=CapabilityType.TOOL,
        name="b",
        description="tool b",
        input_schema={"type": "object", "properties": {}},
    )

    provider = FakeProvider([capability_a, capability_b])
    manager.register_provider(provider)
    await manager.refresh()

    ids = {cap.id for cap in manager.list_capabilities()}
    assert ids == {"tool:a", "tool:b"}

    duplicate_provider = FakeProvider([capability_a])
    manager.register_provider(duplicate_provider)
    with pytest.raises(ValueError):
        await manager.refresh()


def test_tool_manager_tool_defs_include_metadata() -> None:
    manager = ToolManager()
    tool = DummyTool("echo", "Echo input text")

    manager.register_tool(tool)

    tool_defs = manager.list_tool_defs()
    assert tool_defs

    tool_def = tool_defs[0]
    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == "echo"
    assert tool_def["capability_id"] == "tool:echo"
    assert tool_def["function"]["parameters"] == tool.input_schema

    metadata = tool_def.get("metadata", {})
    assert metadata.get("risk_level") == "non_idempotent_effect"
    assert metadata.get("requires_approval") is True
    assert metadata.get("timeout_seconds") == 12
    assert metadata.get("is_work_unit") is False
