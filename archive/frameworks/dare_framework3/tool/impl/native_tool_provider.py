"""Native tool provider implementation."""

from __future__ import annotations

from typing import Any, Callable

from dare_framework3.tool.component import ITool, ICapabilityProvider
from dare_framework3.tool.types import (
    CapabilityDescriptor,
    CapabilityType,
    RunContext,
)


class NativeToolProvider(ICapabilityProvider):
    """Expose local ITool instances as capabilities.
    
    Args:
        tools: List of tool instances to expose
        context_factory: Factory function for creating run contexts
    """

    def __init__(
        self,
        *,
        tools: list[ITool],
        context_factory: Callable[[], RunContext[Any]],
    ) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._context_factory = context_factory

    async def list(self) -> list[CapabilityDescriptor]:
        """List all tool capabilities."""
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

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
    ) -> object:
        """Invoke a tool capability."""
        tool_name = _tool_name(capability_id)
        tool = self._tools.get(tool_name)
        
        if tool is None:
            raise KeyError(f"Unknown tool capability: {capability_id}")
        
        return await tool.execute(params, self._context_factory())


def _capability_id(tool_name: str) -> str:
    """Create a capability ID from a tool name."""
    return f"tool:{tool_name}"


def _tool_name(capability_id: str) -> str:
    """Extract the tool name from a capability ID."""
    prefix = "tool:"
    if not capability_id.startswith(prefix):
        raise ValueError(f"Not a tool capability id: {capability_id}")
    return capability_id[len(prefix):]
