from typing import Any

from dare_framework.context import Context
from dare_framework.plan import Envelope
from dare_framework.tool import IToolGateway, ToolManager, ToolResult, CapabilityDescriptor, RunContext


class ToolGateway(IToolGateway):

    def __init__(self, tool_manager: ToolManager):
        self._tool_manager = tool_manager

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return self._tool_manager.list_capabilities()

    async def invoke(self, capability_id: str, params: dict[str, Any], *, envelope: Envelope,
                     context: Context | None = None) -> ToolResult:
        if envelope.allowed_capability_ids and capability_id not in envelope.allowed_capability_ids:
            raise PermissionError(f"Capability '{capability_id}' not allowed by envelope")
        tool = self._tool_manager.get_tool(capability_id)
        tool_context = RunContext(context)
        return await tool.execute(params, tool_context)
