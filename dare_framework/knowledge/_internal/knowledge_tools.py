"""Knowledge get/add exposed as ITool for agent tool list."""

from __future__ import annotations

from typing import Any, TypedDict

from dare_framework.infra.component import ComponentType
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """Serialize Message-like to dict for tool output."""
    return {
        "role": getattr(msg, "role", "assistant"),
        "content": getattr(msg, "content", ""),
        "name": getattr(msg, "name", None),
        "metadata": getattr(msg, "metadata", {}),
    }


class KnowledgeGetTool(ITool):
    """Tool: retrieve knowledge by query (IKnowledge.get)."""

    def __init__(self, knowledge: IKnowledge) -> None:
        self._knowledge = knowledge

    @property
    def name(self) -> str:
        return "knowledge_get"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return (
            "Retrieve documents from the knowledge base by query. "
            "Call this when the user asks to retrieve, look up, or introduce something that may have been stored in the knowledge base; "
            "then answer based on the returned messages."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    # noinspection PyMethodOverriding
    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        query: str,
        top_k: int = 5,
    ) -> ToolResult[KnowledgeGetOutput]:
        """Retrieve messages from knowledge by query.

        Args:
            run_context: Runtime invocation context.
            query: Search query for retrieval.
            top_k: Maximum number of results to return.

        Returns:
            Retrieved message payloads.
        """
        _ = run_context
        try:
            messages = self._knowledge.get(query, top_k=top_k)
            out = [_message_to_dict(m) for m in messages]
            return ToolResult(success=True, output={"messages": out})
        except Exception as e:
            return ToolResult(success=False, output={}, error=str(e))


class KnowledgeAddTool(ITool):
    """Tool: add content to knowledge base (IKnowledge.add)."""

    def __init__(self, knowledge: IKnowledge) -> None:
        self._knowledge = knowledge

    @property
    def name(self) -> str:
        return "knowledge_add"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return (
            "Add content to the knowledge base. Call once per item; do not repeat for the same content. "
            "Optionally provide metadata (e.g. source, title)."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "idempotent_write"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    # noinspection PyMethodOverriding
    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult[KnowledgeAddOutput]:
        """Add content into the knowledge store.

        Args:
            run_context: Runtime invocation context.
            content: Content text to persist.
            metadata: Optional metadata for the stored content.

        Returns:
            Add operation status payload.
        """
        _ = run_context
        metadata = metadata or {}
        try:
            self._knowledge.add(content, metadata=metadata)
            return ToolResult(
                success=True,
                output={
                    "added": True,
                    "message": "已成功添加 1 条内容到知识库，无需重复调用。",
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output={"added": False, "message": f"添加失败: {e}"},
                error=str(e),
            )


class KnowledgeMessage(TypedDict):
    role: str
    content: str
    name: str | None
    metadata: dict[str, Any]


class KnowledgeGetOutput(TypedDict):
    messages: list[KnowledgeMessage]


class KnowledgeAddOutput(TypedDict):
    added: bool
    message: str


__all__ = ["KnowledgeGetTool", "KnowledgeAddTool"]
