"""Native tool provider implementation.

Manages local ITool instances and exposes them as capabilities.
"""

from __future__ import annotations

from typing import Any, Callable
from enum import Enum

from dare_framework.tool.interfaces import ICapabilityProvider, ITool
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    ProviderStatus,
    RunContext,
    ToolResult,
)


class NativeToolProvider(ICapabilityProvider):
    """Provider for locally registered ITool implementations.
    
    V4 alignment:
    - Converts ITool to CapabilityDescriptor (trusted metadata)
    - Supports dynamic registration/unregistration
    - Provides health check
    """

    def __init__(
        self,
        *,
        tools: list[ITool] | None = None,
        context_factory: Callable[[], RunContext[Any]] | None = None,
        capability_prefix: str | None = None,
    ) -> None:
        self._tools: dict[str, ITool] = {}
        self._run_context: RunContext[Any] = RunContext()
        self._context_factory = context_factory
        if tools:
            for tool in tools:
                self.register_tool(tool)
        if context_factory is not None:
            self._run_context = context_factory()
        if capability_prefix is None:
            self._capability_prefix = "tool:" if tools else ""
        else:
            self._capability_prefix = capability_prefix

    def register_tool(self, tool: ITool) -> None:
        """Register a tool.
        
        Args:
            tool: The tool to register.
            
        Raises:
            ValueError: If tool with same name already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool by name.
        
        Args:
            name: The tool name to unregister.
            
        Returns:
            True if tool was found and removed, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> ITool | None:
        """Get a tool by name.
        
        Args:
            name: The tool name.
            
        Returns:
            The tool or None if not found.
        """
        return self._tools.get(name)

    def set_run_context(self, context: RunContext[Any]) -> None:
        """Set the run context for tool executions.
        
        Args:
            context: The run context to use.
        """
        self._run_context = context

    async def list(self) -> list[CapabilityDescriptor]:
        """List all registered tools as capabilities."""
        capabilities: list[CapabilityDescriptor] = []
        
        for tool in self._tools.values():
            metadata = _capability_metadata(tool)
            capability = CapabilityDescriptor(
                id=_capability_id(self._capability_prefix, tool.name),
                type=CapabilityType.TOOL,
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
                output_schema=tool.output_schema,
                metadata=metadata,
            )
            capabilities.append(capability)
        
        return capabilities

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> ToolResult:
        """Invoke a tool by capability ID.
        
        Args:
            capability_id: The tool name (capability ID).
            params: Parameters to pass to the tool.
            
        Returns:
            ToolResult from the tool execution.
            
        Raises:
            KeyError: If tool not found.
        """
        tool_name = capability_id
        if self._capability_prefix and capability_id.startswith(self._capability_prefix):
            tool_name = capability_id[len(self._capability_prefix):]
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Tool not found: {capability_id}")
        context = self._context_factory() if self._context_factory else self._run_context
        return await tool.execute(params, context)

    async def health_check(self) -> ProviderStatus:
        """Check provider health.
        
        Returns:
            HEALTHY if tools are registered, DEGRADED if empty.
        """
        if len(self._tools) > 0:
            return ProviderStatus.HEALTHY
        return ProviderStatus.DEGRADED

    def list_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions in LLM-compatible format.
        
        Implements IToolProvider for BaseContext integration.
        """
        return [_tool_definition(self._capability_prefix, tool) for tool in self._tools.values()]


def _capability_id(prefix: str, name: str) -> str:
    return f"{prefix}{name}"


def _capability_metadata(tool: ITool) -> CapabilityMetadata:
    metadata: CapabilityMetadata = {}
    risk_level = getattr(tool, "risk_level", "read_only")
    metadata["risk_level"] = str(getattr(risk_level, "value", risk_level))
    metadata["requires_approval"] = bool(getattr(tool, "requires_approval", False))
    timeout_seconds = getattr(tool, "timeout_seconds", None)
    if timeout_seconds is not None:
        metadata["timeout_seconds"] = int(timeout_seconds)
    metadata["is_work_unit"] = bool(getattr(tool, "is_work_unit", False))
    metadata["capability_kind"] = _normalize_capability_kind(
        getattr(tool, "capability_kind", CapabilityKind.TOOL)
    )
    return metadata


def _tool_definition(prefix: str, tool: ITool) -> dict[str, Any]:
    tool_def = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
        "capability_id": _capability_id(prefix, tool.name),
    }
    metadata = _normalize_metadata(dict(_capability_metadata(tool)))
    if metadata:
        tool_def["metadata"] = metadata
    if tool.output_schema:
        tool_def["output_schema"] = dict(tool.output_schema)
    return tool_def


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized[key] = _normalize_value(value)
    return normalized


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _normalize_capability_kind(value: Any) -> CapabilityKind:
    if isinstance(value, CapabilityKind):
        return value
    if hasattr(value, "value"):
        value = value.value
    try:
        return CapabilityKind(str(value))
    except ValueError:
        return CapabilityKind.TOOL


__all__ = ["NativeToolProvider"]
