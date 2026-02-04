"""Knowledge get/add exposed as ITool for agent tool list."""

from __future__ import annotations

from typing import Any

from dare_framework.infra.component import ComponentType
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.tool.kernel import ITool
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
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. keyword or topic the user cares about).",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"},
                            "name": {"type": "string"},
                            "metadata": {"type": "object"},
                        },
                    },
                },
            },
        }

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

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        query = input.get("query", "")
        top_k = input.get("top_k", 5)
        if not isinstance(top_k, int):
            top_k = 5
        try:
            messages = self._knowledge.get(query, top_k=top_k)
            out = [ _message_to_dict(m) for m in messages ]
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
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text content to add to the knowledge base.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata (e.g. source, title).",
                },
            },
            "required": ["content"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "added": {"type": "boolean"},
                "message": {"type": "string", "description": "Human-readable result; 已添加后请勿重复调用."},
            },
        }

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

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        content = input.get("content", "")
        metadata = input.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
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


__all__ = ["KnowledgeGetTool", "KnowledgeAddTool"]
