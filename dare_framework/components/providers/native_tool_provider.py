from __future__ import annotations

from typing import Any, Callable

from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ITool
from dare_framework.core.tool.capabilities import CapabilityDescriptor, CapabilityType, ICapabilityProvider


class NativeToolProvider(ICapabilityProvider):
    """Expose local ITool instances as v2 capabilities."""

    def __init__(self, *, tools: list[ITool], context_factory: Callable[[], RunContext]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._context_factory = context_factory

    async def list(self) -> list[CapabilityDescriptor]:
        capabilities: list[CapabilityDescriptor] = []
        for tool in self._tools.values():
            capabilities.append(
                CapabilityDescriptor(
                    id=_capability_id(tool.name),
                    type=CapabilityType.TOOL,
                    name=tool.name,
                    description=tool.description,
                    input_schema=dict(tool.input_schema),
                    output_schema=dict(tool.output_schema),
                    metadata={
                        "risk_level": getattr(tool.risk_level, "value", str(tool.risk_level)),
                        "requires_approval": bool(tool.requires_approval),
                        "timeout_seconds": int(tool.timeout_seconds),
                        "is_work_unit": bool(tool.is_work_unit),
                    },
                )
            )
        return capabilities

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        tool_name = _tool_name(capability_id)
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Unknown tool capability: {capability_id}")
        return await tool.execute(params, self._context_factory())


def _capability_id(tool_name: str) -> str:
    return f"tool:{tool_name}"


def _tool_name(capability_id: str) -> str:
    prefix = "tool:"
    if not capability_id.startswith(prefix):
        raise ValueError(f"Not a tool capability id: {capability_id}")
    return capability_id[len(prefix) :]
