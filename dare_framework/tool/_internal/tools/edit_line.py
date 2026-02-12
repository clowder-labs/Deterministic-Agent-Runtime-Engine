"""Edit line tool implementation."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
from dare_framework.tool.errors import ToolError
from dare_framework.tool._internal.file_utils import (
    DEFAULT_MAX_BYTES,
    atomic_write,
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


class EditLineTool(ITool):
    """Insert or delete a line at a specific 1-indexed line number."""

    @property
    def name(self) -> str:
        return "edit_line"

    @property
    def description(self) -> str:
        return "Insert or delete a line at a specific 1-indexed line number."

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

    @property
    def risk_level(self) -> str:
        return "non_idempotent_effect"

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
        return [{"type": "file_modified", "produces": {"path": "*"}}]

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
        path: str,
        mode: Literal["insert", "delete"],
        line_number: int = 1,
        text: str = "",
        strict_match: bool = True,
    ) -> ToolResult[EditLineOutput]:
        """Insert or delete a specific line.

        Args:
            run_context: Runtime invocation context.
            path: File path relative to workspace root.
            mode: Edit mode, either insert or delete.
            line_number: 1-indexed target line number.
            text: Text to insert, or expected line text for strict delete matching.
            strict_match: Require exact text match when deleting with `text` provided.

        Returns:
            Edit operation metadata including before/after line values.
        """
        try:
            return _execute_edit(
                {
                    "path": path,
                    "mode": mode,
                    "line_number": line_number,
                    "text": text,
                    "strict_match": strict_match,
                },
                run_context,
            )
        except ToolError as exc:
            return _error_result(exc)


def _execute_edit(input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
    path_value = input.get("path")
    mode = input.get("mode", "insert")
    if mode not in {"insert", "delete"}:
        raise ToolError(code="INVALID_MODE", message="mode must be insert or delete", retryable=False)

    # Missing line_number should use schema default (1), but explicit null remains invalid.
    if "line_number" in input:
        line_number = _parse_line_number(input.get("line_number"))
    else:
        line_number = 1
    text = input.get("text", "")
    strict_match = bool(input.get("strict_match", True))

    if mode == "insert" and not text:
        raise ToolError(code="MISSING_TEXT", message="insert requires text", retryable=False)

    roots = resolve_workspace_roots(context)
    abs_path, root = resolve_path(path_value, roots)

    tool_config = get_tool_config(context, "edit_line")
    max_bytes = coerce_int(tool_config.get("max_bytes"), DEFAULT_MAX_BYTES)

    stat_result = _stat_file(abs_path)
    size_bytes = stat_result.st_size
    if size_bytes > max_bytes:
        raise ToolError(code="FILE_TOO_LARGE", message="file exceeds max_bytes", retryable=False)

    try:
        content = abs_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError(code="DECODE_FAILED", message="failed to decode file", retryable=False) from exc
    except OSError as exc:
        raise ToolError(code="READ_FAILED", message=str(exc), retryable=False) from exc

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
            raise ToolError(code="EMPTY_FILE", message="cannot delete from empty file", retryable=False)
        index = line_number - 1
        if index >= len(lines):
            raise ToolError(code="LINE_OUT_OF_RANGE", message="line not found", retryable=False)
        target = lines[index]
        before = target.rstrip("\r\n")
        if text and strict_match and before != text:
            raise ToolError(code="LINE_MISMATCH", message="target line does not match", retryable=False)
        lines.pop(index)

    new_content = "".join(lines)
    new_size = len(new_content.encode("utf-8"))
    if new_size > max_bytes:
        raise ToolError(code="FILE_TOO_LARGE", message="result exceeds max_bytes", retryable=False)

    atomic_write(abs_path, new_content.encode("utf-8"), mode=stat_result.st_mode)

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


def _stat_file(path):
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


def _parse_line_number(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ToolError(code="INVALID_LINE", message="line_number must be an integer") from exc
    if parsed < 1:
        raise ToolError(code="INVALID_LINE", message="line_number must be >= 1", retryable=False)
    return parsed


def _detect_newline(content: str) -> str:
    if "\r\n" in content:
        return "\r\n"
    return "\n"


def _error_result(error: ToolError) -> ToolResult:
    return ToolResult(
        success=False,
        output={"code": error.code},
        error=error.message,
        evidence=[],
    )


class EditLineOutput(TypedDict):
    path: str
    mode: Literal["insert", "delete"]
    line_number: int
    before: str
    after: str
