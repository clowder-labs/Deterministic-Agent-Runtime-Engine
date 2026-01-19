"""
Edit Line Tool

验证点：
1. 基于行号的读改写是否满足计划工具的可表达性
2. 非幂等写入的风险级别如何标注
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dare_framework.components.base_component import BaseComponent
from dare_framework.contracts.evidence import Evidence
from dare_framework.contracts.ids import generator_id
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolResult, ToolType


class EditLineTool(BaseComponent):
    """
    编辑指定行工具

    功能：按行号插入或删除指定文本
    风险级别：NON_IDEMPOTENT_EFFECT（重复调用会产生不同结果）
    """

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    @property
    def name(self) -> str:
        return "edit_line"

    @property
    def description(self) -> str:
        return """Insert or delete a line at a given line number.

Modes:
- insert: inserts text at the 1-indexed line number
- delete: removes the line at the 1-indexed line number (optionally require exact match)
"""

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target file path (relative to workspace)",
                },
                "line_number": {
                    "type": "integer",
                    "description": "1-indexed line number to insert/delete",
                    "default": 1,
                },
                "text": {
                    "type": "string",
                    "description": "Line text to insert or match for delete",
                },
                "mode": {"type": "string", "enum": ["insert", "delete"], "default": "insert"},
                "strict_match": {
                    "type": "boolean",
                    "description": "When deleting, require the target line to equal text",
                    "default": True,
                },
            },
            "required": ["path", "mode"],
        }

    @property
    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "mode": {"type": "string"},
                "line_number": {"type": "integer"},
                "before": {"type": "string"},
                "after": {"type": "string"},
            },
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.NON_IDEMPOTENT_EFFECT

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 10

    @property
    def produces_assertions(self) -> list:
        return [{"type": "file_modified", "produces": {"path": "*"}}]

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        path = input["path"]
        mode = input.get("mode", "insert")
        line_number = int(input.get("line_number", 1))
        text = input.get("text", "")
        strict_match = bool(input.get("strict_match", True))

        if mode not in {"insert", "delete"}:
            return ToolResult(success=False, output={}, error=f"unsupported mode: {mode}", evidence=[])
        if mode == "insert" and not text:
            return ToolResult(success=False, output={}, error="insert mode requires text", evidence=[])

        try:
            abs_path = self._resolve_path(path)
        except ValueError as exc:
            return ToolResult(success=False, output={}, error=str(exc), evidence=[])

        try:
            content = abs_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ToolResult(success=False, output={}, error=f"file not found: {path}", evidence=[])
        except PermissionError:
            return ToolResult(success=False, output={}, error=f"permission denied: {path}", evidence=[])

        newline = _detect_newline(content)
        lines = content.splitlines(keepends=True)
        line_number = max(1, line_number)

        before = ""
        after = ""

        if mode == "insert":
            index = min(line_number - 1, len(lines))
            insert_line = text
            if not insert_line.endswith(("\n", "\r\n")):
                insert_line += newline
            lines.insert(index, insert_line)
            after = insert_line.rstrip("\r\n")
        else:
            if not lines:
                return ToolResult(success=False, output={}, error="cannot delete from empty file", evidence=[])
            index = line_number - 1
            if index >= len(lines):
                return ToolResult(success=False, output={}, error=f"line {line_number} not found", evidence=[])
            target = lines[index]
            before = target.rstrip("\r\n")
            if text and strict_match and before != text:
                return ToolResult(
                    success=False,
                    output={"before": before},
                    error="target line does not match provided text",
                    evidence=[],
                )
            lines.pop(index)

        try:
            abs_path.write_text("".join(lines), encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, output={}, error=str(exc), evidence=[])

        return ToolResult(
            success=True,
            output={
                "path": str(abs_path),
                "mode": mode,
                "line_number": line_number,
                "before": before,
                "after": after,
            },
            evidence=[
                Evidence(
                    evidence_id=generator_id("evidence"),
                    kind="file_edit",
                    payload={"path": str(abs_path), "mode": mode, "line_number": line_number},
                )
            ],
        )

    def _resolve_path(self, path: str) -> Path:
        resolved = (self._workspace / path).resolve()
        if not resolved.is_relative_to(self._workspace):
            raise ValueError(f"path traversal attempt: {path}")
        return resolved


def _detect_newline(content: str) -> str:
    # Preserve original newline style when inserting.
    if "\r\n" in content:
        return "\r\n"
    return "\n"
