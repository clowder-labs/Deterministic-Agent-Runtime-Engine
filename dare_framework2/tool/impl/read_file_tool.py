"""Read file tool implementation (workspace-root scoped)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dare_framework2.tool.interfaces import ITool
from dare_framework2.tool.types import Evidence, RiskLevel, RunContext, ToolResult, ToolType
from dare_framework2.tool.impl._file_utils import (
    DEFAULT_MAX_BYTES,
    coerce_int,
    get_tool_config,
    relative_to_root,
    resolve_path,
    resolve_workspace_roots,
)
from dare_framework2.utils.ids import generate_id


class ReadFileTool(ITool):
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
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.READ_ONLY

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
        size_bytes = stat_result.st_size
        if size_bytes > max_bytes:
            return _error("FILE_TOO_LARGE")

        encoding = input.get("encoding", "utf-8")
        if not isinstance(encoding, str) or not encoding:
            return _error("INVALID_ENCODING")

        content = _safe_read_text(abs_path, encoding=encoding)
        if content is None:
            return _error("READ_FAILED")

        lines = content.splitlines(keepends=True)
        line_count = len(lines)

        start_line = _parse_optional_line(input.get("start_line"))
        end_line = _parse_optional_line(input.get("end_line"))
        if start_line == -1 or end_line == -1:
            return _error("INVALID_LINE_RANGE")
        if start_line is not None and end_line is not None and end_line < start_line:
            return _error("INVALID_LINE_RANGE")

        truncated = False
        if start_line is not None or end_line is not None:
            if line_count == 0:
                content = ""
            else:
                start_idx = (start_line - 1) if start_line is not None else 0
                if start_idx >= line_count:
                    return _error("LINE_RANGE_OUT_OF_BOUNDS")
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


def _safe_stat(path: Path):
    try:
        return path.stat()
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _safe_read_text(path: Path, *, encoding: str) -> str | None:
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        return None
    except OSError:
        return None


def _parse_optional_line(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return -1
    if parsed < 1:
        return -1
    return parsed


def _error(code: str) -> ToolResult:
    # Keep error surface stable and non-sensitive: return codes only.
    return ToolResult(success=False, output={}, error=code, evidence=[])

