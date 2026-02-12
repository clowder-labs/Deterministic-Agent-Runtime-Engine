"""Read file tool implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
from dare_framework.tool.errors import ToolError
from dare_framework.tool._internal.file_utils import (
    DEFAULT_MAX_BYTES,
    coerce_int,
    get_tool_config,
    relative_to_root,
    resolve_path,
    resolve_workspace_roots,
)
from dare_framework.infra.ids import generate_id
from dare_framework.tool.types import (
    CapabilityKind,
    Evidence,
    RunContext,
    ToolResult,
    ToolType,
)


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
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

    @property
    def risk_level(self) -> str:
        return "read_only"

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

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    # noinspection PyMethodOverriding
    async def execute(
        self,
        run_context: RunContext[Any] | dict[str, Any],
        path: str | RunContext[Any],
        encoding: str = "utf-8",
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult[ReadFileOutput]:
        """Read text content from a file path.

        Args:
            run_context: Runtime invocation context.
            path: File path relative to workspace root.
            encoding: Text encoding used for decoding file content.
            start_line: Optional 1-indexed start line for partial reads.
            end_line: Optional 1-indexed end line for partial reads.

        Returns:
            File content payload with metadata.
        """
        normalized = _normalize_execute_args(
            run_context=run_context,
            path=path,
            encoding=encoding,
            start_line=start_line,
            end_line=end_line,
        )
        if isinstance(normalized, ToolResult):
            return normalized
        run_context, path, encoding, start_line, end_line = normalized

        try:
            payload: dict[str, Any] = {
                "path": path,
                "encoding": encoding,
            }
            if start_line is not None:
                payload["start_line"] = start_line
            if end_line is not None:
                payload["end_line"] = end_line
            return _execute_read(payload, run_context)
        except ToolError as exc:
            return _error_result(exc)


def _normalize_execute_args(
    *,
    run_context: RunContext[Any] | dict[str, Any],
    path: str | RunContext[Any],
    encoding: str,
    start_line: int | None,
    end_line: int | None,
) -> tuple[RunContext[Any], str, str, int | None, int | None] | ToolResult:
    """Support both keyword invocation and legacy input/context invocation."""

    if isinstance(run_context, dict):
        if not isinstance(path, RunContext):
            return ToolResult(
                success=False,
                output={"code": "INVALID_CONTEXT"},
                error="run context is required",
                evidence=[],
            )
        input_payload = run_context
        parsed_path = input_payload.get("path")
        parsed_encoding = input_payload.get("encoding", encoding)
        parsed_start = input_payload.get("start_line", start_line)
        parsed_end = input_payload.get("end_line", end_line)
        return path, str(parsed_path) if parsed_path is not None else "", parsed_encoding, parsed_start, parsed_end
    if isinstance(path, RunContext):
        return ToolResult(
            success=False,
            output={"code": "INVALID_PATH"},
            error="path is required",
            evidence=[],
        )
    return run_context, path, encoding, start_line, end_line


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


class ReadFileOutput(TypedDict):
    content: str
    path: str
    size_bytes: int
    line_count: int
    truncated: bool
