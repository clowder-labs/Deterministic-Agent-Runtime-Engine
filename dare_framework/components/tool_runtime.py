from __future__ import annotations

from typing import Any

from ..core.errors import ApprovalRequired, ToolAccessDenied, ToolError, ToolNotFoundError
from ..core.interfaces import IPolicyEngine, IToolRuntime, IToolkit, ISkillRegistry, IValidator
from ..core.models import DonePredicate, Envelope, RunContext, ToolResult, PolicyDecision


class ToolRuntime(IToolRuntime):
    def __init__(
        self,
        toolkit: IToolkit,
        skill_registry: ISkillRegistry,
        policy_engine: IPolicyEngine,
        validator: IValidator,
    ) -> None:
        self._toolkit = toolkit
        self._skill_registry = skill_registry
        self._policy_engine = policy_engine
        self._validator = validator

    async def invoke(
        self,
        name: str,
        input: dict[str, Any],
        ctx: RunContext,
        envelope: Envelope | None = None,
    ) -> ToolResult:
        tool = self.get_tool(name)
        if tool is None:
            raise ToolNotFoundError(f"Unknown tool: {name}")

        decision = self._policy_engine.check_tool_access(tool, ctx)
        if decision == PolicyDecision.DENY:
            raise ToolAccessDenied(f"Tool access denied: {name}")
        if decision == PolicyDecision.APPROVE_REQUIRED:
            raise ApprovalRequired(f"Tool requires approval: {name}")

        if envelope is not None and (tool.is_work_unit or envelope.done_predicate):
            return await self._tool_loop(tool, input, ctx, envelope)

        return await self._execute_tool(tool, input, ctx)

    def get_tool(self, name: str):
        return self._toolkit.get_tool(name)

    def list_tools(self):
        return self._toolkit.list_tools()

    def is_plan_tool(self, name: str) -> bool:
        return self._skill_registry.get_skill(name) is not None

    async def _execute_tool(self, tool, input: dict[str, Any], ctx: RunContext) -> ToolResult:
        try:
            return await tool.execute(input, ctx)
        except ToolError as exc:
            return ToolResult(success=False, output={}, error=exc.message, evidence=[])

    async def _tool_loop(
        self,
        tool,
        input: dict[str, Any],
        ctx: RunContext,
        envelope: Envelope,
    ) -> ToolResult:
        if envelope.allowed_tools and tool.name not in envelope.allowed_tools:
            return ToolResult(
                success=False,
                output={},
                error=f"Tool {tool.name} not allowed by envelope",
                evidence=[],
            )
        predicate = envelope.done_predicate or DonePredicate()
        max_iterations = max(1, envelope.budget.max_tool_calls)
        last_result = ToolResult(success=False, output={}, error="Tool loop not executed", evidence=[])
        for _ in range(max_iterations):
            result = await self._execute_tool(tool, input, ctx)
            last_result = result
            if not result.success:
                continue
            if await self._validator.validate_evidence(result.evidence, predicate):
                return result
        return ToolResult(
            success=False,
            output=last_result.output,
            error=last_result.error or "Tool loop budget exhausted",
            evidence=last_result.evidence,
        )
