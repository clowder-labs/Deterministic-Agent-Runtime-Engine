"""Read file tool implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dare_framework3_4.security.types import RiskLevel
from dare_framework3_4.tool.component import ITool
from dare_framework3_4.tool.errors import ToolError
from dare_framework3_4.tool.internal.file_utils import (
    DEFAULT_MAX_BYTES,
    coerce_int,
    get_tool_config,
    relative_to_root,
    resolve_path,
    resolve_workspace_roots,
)
from dare_framework3_4.tool.internal.ids import generate_id
from dare_framework3_4.tool.types import Evidence, RunContext, ToolResult, ToolType


class ReadFileTool(ITool):
    """Read text content from a file within the workspace roots."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read text content from a file within the workspace roots."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace root"},
                "encoding": {"type": "string", "default": "utf-8"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "path": {"type": "string"},
                "size_bytes": {"type": "integer"},
                "line_count": {"type": "integer"},
                "truncated": {"type": "boolean"},
            },
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.READ_ONLY

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
    def produces_assertions(self) -> list[dict[str, Any]]:
        return [{"type": "file_content", "produces": {"path": "*"}}]

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        try:
            return _execute_read(input, context)
        except ToolError as exc:
            return _error_result(exc)


def _execute_read(input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
    roots = resolve_workspace_roots(context)
    path_value = input.get("path")
    abs_path, root = resolve_path(path_value, roots)

    tool_config = get_tool_config(context, "read_file")
    max_bytes = coerce_int(tool_config.get("max_bytes"), DEFAULT_MAX_BYTES)

    stat_result = _stat_file(abs_path)
    size_bytes = stat_result.st_size
    if size_bytes > max_bytes:
        raise ToolError(code="FILE_TOO_LARGE", message="file exceeds max_bytes", retryable=False)

    encoding = input.get("encoding", "utf-8")
    if not isinstance(encoding, str) or not encoding:
        raise ToolError(code="INVALID_ENCODING", message="encoding must be a string", retryable=False)

    try:
        content = abs_path.read_text(encoding=encoding)
    except UnicodeDecodeError as exc:
        raise ToolError(code="DECODE_FAILED", message="failed to decode file", retryable=False) from exc
    except OSError as exc:
        raise ToolError(code="READ_FAILED", message=str(exc), retryable=False) from exc

    lines = content.splitlines(keepends=True)
    line_count = len(lines)

    start_line = _parse_optional_line(input.get("start_line"), "start_line")
    end_line = _parse_optional_line(input.get("end_line"), "end_line")
    if start_line is not None and start_line < 1:
        raise ToolError(code="INVALID_LINE_RANGE", message="start_line must be >= 1", retryable=False)
    if end_line is not None and end_line < 1:
        raise ToolError(code="INVALID_LINE_RANGE", message="end_line must be >= 1", retryable=False)
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ToolError(code="INVALID_LINE_RANGE", message="end_line must be >= start_line", retryable=False)

    truncated = False
    if start_line is not None or end_line is not None:
        if line_count == 0:
            content = ""
        else:
            start_idx = (start_line - 1) if start_line is not None else 0
            if start_idx >= line_count:
                raise ToolError(
                    code="LINE_RANGE_OUT_OF_BOUNDS",
                    message="start_line out of range",
                )
            end_idx = end_line if end_line is not None else line_count
            if end_idx > line_count:
                end_idx = line_count
            content = "".join(lines[start_idx:end_idx])
        truncated = not (
            (start_line is None or start_line == 1)
            and (end_line is None or end_line >= line_count)
        )

    rel_path = relative_to_root(abs_path, root)
    return ToolResult(
        success=True,
        output={
            "content": content,
            "path": rel_path,
            "size_bytes": size_bytes,
            "line_count": line_count,
            "truncated": truncated,
        },
        evidence=[
            Evidence(
                evidence_id=generate_id("evidence"),
                kind="file_read",
                payload={"path": rel_path},
            )
        ],
    )


def _stat_file(path: Path):
    try:
        stat_result = path.stat()
    except FileNotFoundError as exc:
        raise ToolError(code="FILE_NOT_FOUND", message="file not found", retryable=False) from exc
    except PermissionError as exc:
        raise ToolError(code="PERMISSION_DENIED", message="permission denied", retryable=False) from exc
    except OSError as exc:
        raise ToolError(code="READ_FAILED", message=str(exc), retryable=False) from exc
    if not path.is_file():
        raise ToolError(code="INVALID_PATH", message="path is not a file", retryable=False)
    return stat_result


def _parse_optional_line(value: Any, name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolError(code="INVALID_LINE_RANGE", message=f"{name} must be an integer") from exc


def _error_result(error: ToolError) -> ToolResult:
    return ToolResult(
        success=False,
        output={"code": error.code},
        error=error.message,
        evidence=[],
    )
