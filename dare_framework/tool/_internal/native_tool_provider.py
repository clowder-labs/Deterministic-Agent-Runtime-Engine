"""In-process capability provider for local ITool instances."""

from __future__ import annotations

from typing import Any, Callable

from dare_framework.tool.interfaces import ICapabilityProvider, ITool, RunContext
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
)


class NativeToolProvider(ICapabilityProvider):
    """Expose local tools as capability descriptors."""

    def __init__(self, *, tools: list[ITool], context_factory: Callable[[], RunContext[Any]]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._context_factory = context_factory

    async def list(self) -> list[CapabilityDescriptor]:
        capabilities: list[CapabilityDescriptor] = []
        for tool in self._tools.values():
            capabilities.append(_capability_from_tool(tool))
        return capabilities

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        tool_name = _tool_name(capability_id)
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Unknown tool capability: {capability_id}")
        return await tool.execute(params, self._context_factory())


def _capability_from_tool(tool: ITool) -> CapabilityDescriptor:
    description = getattr(tool, "description", "")
    input_schema = getattr(tool, "input_schema", None)
    if not isinstance(input_schema, dict):
        input_schema = {"type": "object", "properties": {}}

    output_schema = getattr(tool, "output_schema", None)
    if output_schema is not None and not isinstance(output_schema, dict):
        output_schema = None

    metadata = _tool_metadata(tool)

    return CapabilityDescriptor(
        id=_capability_id(tool.name),
        type=CapabilityType.TOOL,
        name=tool.name,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        metadata=metadata,
    )


def _tool_metadata(tool: ITool) -> CapabilityMetadata | None:
    metadata: CapabilityMetadata = {}

    risk_level = getattr(tool, "risk_level", None)
    if risk_level is not None:
        metadata["risk_level"] = _stringify_risk_level(risk_level)

    requires_approval = getattr(tool, "requires_approval", None)
    if requires_approval is not None:
        metadata["requires_approval"] = bool(requires_approval)

    timeout_seconds = getattr(tool, "timeout_seconds", None)
    if timeout_seconds is not None:
        metadata["timeout_seconds"] = int(timeout_seconds)

    is_work_unit = getattr(tool, "is_work_unit", None)
    if is_work_unit is not None:
        metadata["is_work_unit"] = bool(is_work_unit)

    capability_kind = getattr(tool, "capability_kind", None)
    if capability_kind is not None:
        try:
            metadata["capability_kind"] = CapabilityKind(capability_kind)
        except ValueError:
            pass

    return metadata or None


def _stringify_risk_level(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _capability_id(tool_name: str) -> str:
    return f"tool:{tool_name}"


def _tool_name(capability_id: str) -> str:
    prefix = "tool:"
    if not capability_id.startswith(prefix):
        raise ValueError(f"Not a tool capability id: {capability_id}")
    return capability_id[len(prefix) :]


__all__ = ["NativeToolProvider"]
