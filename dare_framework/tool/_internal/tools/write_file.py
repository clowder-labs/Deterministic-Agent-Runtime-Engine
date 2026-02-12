"""Write file tool implementation."""

from __future__ import annotations

from typing import Any, TypedDict

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


class WriteFileTool(ITool):
    """Write text content to a file within the workspace roots."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write text content to a file within the workspace roots."

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

    @property
    def risk_level(self) -> str:
        return "idempotent_write"

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
        run_context: RunContext[Any] | dict[str, Any],
        path: str | RunContext[Any],
        content: str | None = None,
        create_dirs: bool = True,
    ) -> ToolResult[WriteFileOutput]:
        """Write text content into a workspace file.

        Args:
            run_context: Runtime invocation context.
            path: File path relative to workspace root.
            content: UTF-8 text content to write.
            create_dirs: Whether to create missing parent directories.

        Returns:
            Write result metadata including bytes written and creation state.
        """
        normalized = _normalize_execute_args(
            run_context=run_context,
            path=path,
            content=content,
            create_dirs=create_dirs,
        )
        if isinstance(normalized, ToolResult):
            return normalized
        run_context, path, content, create_dirs = normalized

        try:
            return _execute_write(
                {"path": path, "content": content, "create_dirs": create_dirs},
                run_context,
            )
        except ToolError as exc:
            return _error_result(exc)


def _normalize_execute_args(
    *,
    run_context: RunContext[Any] | dict[str, Any],
    path: str | RunContext[Any],
    content: str | None,
    create_dirs: bool,
) -> tuple[RunContext[Any], str, str | None, bool] | ToolResult:
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
        parsed_content = input_payload.get("content", content)
        parsed_create_dirs = input_payload.get("create_dirs", create_dirs)
        return path, str(parsed_path) if parsed_path is not None else "", parsed_content, bool(parsed_create_dirs)
    if isinstance(path, RunContext):
        return ToolResult(
            success=False,
            output={"code": "INVALID_PATH"},
            error="path is required",
            evidence=[],
        )
    return run_context, path, content, create_dirs


def _execute_write(input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
    path_value = input.get("path")
    content = input.get("content")
    if not isinstance(content, str):
        raise ToolError(code="INVALID_CONTENT", message="content must be a string", retryable=False)

    roots = resolve_workspace_roots(context)
    abs_path, root = resolve_path(path_value, roots)
    if abs_path.exists() and abs_path.is_dir():
        raise ToolError(code="INVALID_PATH", message="path is a directory", retryable=False)

    tool_config = get_tool_config(context, "write_file")
    max_bytes = coerce_int(tool_config.get("max_bytes"), DEFAULT_MAX_BYTES)

    content_bytes = content.encode("utf-8")
    if len(content_bytes) > max_bytes:
        raise ToolError(code="CONTENT_TOO_LARGE", message="content exceeds max_bytes", retryable=False)

    create_dirs = input.get("create_dirs", True)
    if create_dirs:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
    elif not abs_path.parent.exists():
        raise ToolError(code="MISSING_PARENT", message="parent directory does not exist", retryable=False)

    created = not abs_path.exists()
    mode = None
    if abs_path.exists():
        try:
            mode = abs_path.stat().st_mode
        except OSError:
            mode = None
    atomic_write(abs_path, content_bytes, mode=mode)

    rel_path = relative_to_root(abs_path, root)
    return ToolResult(
        success=True,
        output={
            "path": rel_path,
            "bytes_written": len(content_bytes),
            "created": created,
        },
        evidence=[
            Evidence(
                evidence_id=generate_id("evidence"),
                kind="file_write",
                payload={"path": rel_path},
            )
        ],
    )


def _error_result(error: ToolError) -> ToolResult:
    return ToolResult(
        success=False,
        output={"code": error.code},
        error=error.message,
        evidence=[],
    )


class WriteFileOutput(TypedDict):
    path: str
    bytes_written: int
    created: bool
