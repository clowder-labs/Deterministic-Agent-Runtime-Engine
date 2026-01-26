"""Native tool provider implementation.

Manages local ITool instances and exposes them as capabilities.
"""

from __future__ import annotations

from typing import Any, Callable

from dare_framework3_4.tool.interfaces import ICapabilityProvider, ITool
from dare_framework3_4.tool.types import (
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
            risk_level = getattr(tool.risk_level, "value", tool.risk_level)
            metadata = CapabilityMetadata(
                risk_level=str(risk_level),
                requires_approval=tool.requires_approval,
                timeout_seconds=tool.timeout_seconds,
                is_work_unit=tool.is_work_unit,
                capability_kind=CapabilityKind.TOOL,
            )
            
            capability = CapabilityDescriptor(
                id=f\"{self._capability_prefix}{tool.name}\",
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
        tool_defs: list[dict[str, Any]] = []
        
        for tool in self._tools.values():
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            tool_defs.append(tool_def)
        
        return tool_defs


__all__ = ["NativeToolProvider"]
