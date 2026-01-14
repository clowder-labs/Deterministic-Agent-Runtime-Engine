from __future__ import annotations

from typing import Any

from ..core.errors import ToolError
from ..core.interfaces import IToolkit
from ..core.models import Evidence, RunContext, ToolDefinition, ToolResult, ToolRiskLevel, ToolType, new_id
from .base_component import BaseComponent


class CompositeTool(BaseComponent):
    """Simple sequential composite tool driven by config recipes."""

    def __init__(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        toolkit: IToolkit,
    ) -> None:
        self._name = name
        self._description = description or f"Composite tool: {name}"
        self._steps = steps
        self._toolkit = toolkit

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        # Pass-through: optional per-step overrides may merge inputs.
        return {"type": "object", "properties": {}, "additionalProperties": True}

    @property
    def output_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"steps": {"type": "array"}}}

    @property
    def risk_level(self):
        return ToolRiskLevel.READ_ONLY

    @property
    def tool_type(self) -> ToolType:
        return ToolType.WORKUNIT

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def produces_assertions(self) -> list[dict]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return True

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        results: list[dict[str, Any]] = []
        evidence: list[Evidence] = []
        for step in self._steps:
            tool_name = step.get("tool")
            if not tool_name:
                return ToolResult(
                    success=False,
                    output={"steps": results},
                    error="composite tool step missing 'tool'",
                    evidence=evidence,
                )
            tool = self._toolkit.get_tool(tool_name)
            if tool is None:
                return ToolResult(
                    success=False,
                    output={"steps": results},
                    error=f"composite tool missing dependency: {tool_name}",
                    evidence=evidence,
                )
            step_input = dict(step.get("input", {}))
            # Allow caller input to override step input where keys match.
            if input:
                step_input.update({k: v for k, v in input.items() if k not in step_input})
            try:
                result = await tool.execute(step_input, context)
            except ToolError as exc:
                return ToolResult(
                    success=False,
                    output={"steps": results},
                    error=exc.message,
                    evidence=evidence,
                )
            results.append(
                {
                    "tool": tool_name,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
            )
            evidence.extend(result.evidence)
            if not result.success:
                return ToolResult(
                    success=False,
                    output={"steps": results},
                    error=result.error or "composite tool step failed",
                    evidence=evidence,
                )
        # Add a composite evidence marker for traceability.
        evidence.append(
            Evidence(
                evidence_id=new_id("evidence"),
                kind="composite_tool",
                payload={"name": self._name, "steps": [s.get("tool") for s in self._steps]},
            )
        )
        return ToolResult(
            success=True,
            output={"steps": results},
            error=None,
            evidence=evidence,
        )
