from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dare_framework.components.interfaces import IPolicyEngine, IToolRuntime, PolicyDecision
from dare_framework.components.toolkit import BasicToolkit
from dare_framework.core.errors import PolicyDeniedError, ToolExecutionError
from dare_framework.core.models import Envelope, RunContext, ToolDefinition, ToolResult


@dataclass
class DefaultToolRuntime(IToolRuntime):
    def __init__(self, toolkit: BasicToolkit, policy_engine: IPolicyEngine) -> None:
        self._toolkit = toolkit
        self._policy_engine = policy_engine

    async def invoke(
        self,
        name: str,
        input: dict[str, Any],
        ctx: RunContext,
        envelope: Envelope | None = None,
    ) -> ToolResult:
        tool = self._toolkit.get_tool(name)
        if not tool:
            raise ToolExecutionError(f"Unknown tool: {name}")

        decision = self._policy_engine.check_tool_access(tool, ctx)
        if decision == PolicyDecision.DENY:
            raise PolicyDeniedError(f"Policy denied tool: {name}")

        return await tool.execute(input, ctx)

    def get_tool(self, name: str):
        return self._toolkit.get_tool(name)

    def list_tools(self) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []
        for tool in self._toolkit.list_tools():
            definitions.append(
                ToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.get_input_schema(),
                    tool_type=tool.tool_type,
                    risk_level=tool.risk_level,
                    is_plan_tool=False,
                )
            )
        return definitions

    def is_plan_tool(self, name: str) -> bool:
        return False
