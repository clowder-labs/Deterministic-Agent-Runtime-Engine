from __future__ import annotations

from typing import Any, TypedDict

import pytest

from dare_framework.infra.component import ComponentType
from dare_framework.plan.types import Envelope
from dare_framework.tool.kernel import ITool
from dare_framework.tool.tool_gateway import ToolGateway
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.tool.types import CapabilityKind, RunContext, ToolResult, ToolType


class _SearchOutput(TypedDict):
    matches: list[str]
    count: int


class _InferredContractTool(ITool):
    @property
    def name(self) -> str:
        return "inferred_contract"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return "Tool whose schema comes from execute signature."

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 10

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        query: str,
        limit: int | None = None,
    ) -> ToolResult[_SearchOutput]:
        """Search for entries.

        Args:
            run_context: Runtime context for invocation metadata.
            query: Search query text.
            limit: Maximum number of items to return.

        Returns:
            Search result payload containing matches and count.
        """
        _ = run_context
        out: _SearchOutput = {"matches": [query], "count": 1}
        return ToolResult(success=True, output=out)


class _KeywordProbeTool(ITool):
    def __init__(self) -> None:
        self.captured: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "keyword_probe"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return "Capture keyword args passed by gateway."

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 10

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(self, *, run_context: RunContext[Any], message: str) -> ToolResult[dict[str, str]]:
        """Capture run-time arguments.

        Args:
            run_context: Invocation context provided by the runtime.
            message: Message to capture.

        Returns:
            Echo payload with captured message.
        """
        self.captured = {"message": message, "run_context": run_context}
        return ToolResult(success=True, output={"echo": message})


def test_tool_schema_is_inferred_from_execute_signature() -> None:
    manager = ToolManager(load_entrypoints=False)
    descriptor = manager.register_tool(_InferredContractTool())

    assert descriptor.input_schema["type"] == "object"
    assert set(descriptor.input_schema["properties"].keys()) == {"query", "limit"}
    assert descriptor.input_schema["required"] == ["query"]
    assert descriptor.input_schema["properties"]["query"]["type"] == "string"
    assert descriptor.input_schema["properties"]["query"]["description"] == "Search query text."
    limit_schema = descriptor.input_schema["properties"]["limit"]
    assert any(option.get("type") == "integer" for option in limit_schema.get("anyOf", []))
    assert descriptor.output_schema is not None
    assert descriptor.output_schema["type"] == "object"
    assert set(descriptor.output_schema["properties"].keys()) == {"matches", "count"}


@pytest.mark.asyncio
async def test_gateway_invokes_tool_with_keyword_arguments() -> None:
    manager = ToolManager(load_entrypoints=False)
    tool = _KeywordProbeTool()
    descriptor = manager.register_tool(tool)
    gateway = ToolGateway(manager)

    result = await gateway.invoke(
        descriptor.id,
        envelope=Envelope(allowed_capability_ids=[descriptor.id]),
        message="hello",
    )

    assert result.success is True
    assert tool.captured["message"] == "hello"
    assert isinstance(tool.captured["run_context"], RunContext)
