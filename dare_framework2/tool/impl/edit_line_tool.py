"""Edit line tool implementation (workspace-root scoped)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dare_framework2.tool.interfaces import ITool
from dare_framework2.tool.types import Evidence, RiskLevel, RunContext, ToolResult, ToolType
from dare_framework2.tool.impl._file_utils import (
    DEFAULT_MAX_BYTES,
    atomic_write,
    coerce_int,
    get_tool_config,
    relative_to_root,
    resolve_path,
    resolve_workspace_roots,
)
from dare_framework2.utils.ids import generate_id


class EditLineTool(ITool):
    @property
    def name(self) -> str:
        return "edit_line"

    @property
    def description(self) -> str:
        return "Insert or delete a line at a specific 1-indexed line number."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace root"},
                "line_number": {"type": "integer", "minimum": 1, "default": 1},
                "text": {"type": "string"},
                "mode": {"type": "string", "enum": ["insert", "delete"], "default": "insert"},
                "strict_match": {"type": "boolean", "default": True},
            },
            "required": ["path", "mode"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
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
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.NON_IDEMPOTENT_EFFECT

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 10

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        mode = input.get("mode", "insert")
        if mode not in {"insert", "delete"}:
            return _error("INVALID_MODE")

        line_number = _parse_line_number(input.get("line_number"))
        if line_number is None:
            return _error("INVALID_LINE")

        text = input.get("text", "")
        if not isinstance(text, str):
            text = str(text)
        strict_match = bool(input.get("strict_match", True))

        if mode == "insert" and not text:
            return _error("MISSING_TEXT")

        roots = resolve_workspace_roots(context)
        try:
            abs_path, root = resolve_path(input.get("path"), roots)
        except ValueError:
            return _error("INVALID_PATH")
        except PermissionError:
            return _error("PATH_NOT_ALLOWED")

        tool_config = get_tool_config(context, self.name)
        max_bytes = coerce_int(tool_config.get("max_bytes"), DEFAULT_MAX_BYTES)

        stat_result = _safe_stat(abs_path)
        if stat_result is None:
            return _error("FILE_NOT_FOUND")
        if not abs_path.is_file():
            return _error("INVALID_PATH")
        if stat_result.st_size > max_bytes:
            return _error("FILE_TOO_LARGE")

        content = _safe_read_text(abs_path)
        if content is None:
            return _error("READ_FAILED")

        newline = _detect_newline(content)
        lines = content.splitlines(keepends=True)
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
                return _error("EMPTY_FILE")
            index = line_number - 1
            if index >= len(lines):
                return _error("LINE_OUT_OF_RANGE")
            target = lines[index]
            before = target.rstrip("\r\n")
            if text and strict_match and before != text:
                return _error("LINE_MISMATCH")
            lines.pop(index)

        new_content = "".join(lines)
        if len(new_content.encode("utf-8")) > max_bytes:
            return _error("FILE_TOO_LARGE")

        try:
            atomic_write(abs_path, new_content.encode("utf-8"), mode=stat_result.st_mode)
        except OSError:
            return _error("WRITE_FAILED")

        rel_path = relative_to_root(abs_path, root)
        return ToolResult(
            success=True,
            output={
                "path": rel_path,
                "mode": mode,
                "line_number": line_number,
                "before": before,
                "after": after,
            },
            evidence=[
                Evidence(
                    evidence_id=generate_id("evidence"),
                    kind="file_edit",
                    payload={"path": rel_path, "mode": mode, "line_number": line_number},
                )
            ],
        )


def _safe_stat(path: Path):
    try:
        return path.stat()
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _safe_read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError:
        return None


def _parse_line_number(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 1:
        return None
    return parsed


def _detect_newline(content: str) -> str:
    if "\r\n" in content:
        return "\r\n"
    return "\n"


def _error(code: str) -> ToolResult:
    return ToolResult(success=False, output={}, error=code, evidence=[])

