"""Write file tool implementation (workspace-root scoped, atomic replace)."""

from __future__ import annotations

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


class WriteFileTool(ITool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write text content to a file within the workspace roots."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace root"},
                "content": {"type": "string", "description": "Text content to write"},
                "create_dirs": {"type": "boolean", "default": True},
            },
            "required": ["path", "content"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "bytes_written": {"type": "integer"},
                "created": {"type": "boolean"},
            },
        }

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.IDEMPOTENT_WRITE

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
        content = input.get("content")
        if not isinstance(content, str):
            return _error("INVALID_CONTENT")

        roots = resolve_workspace_roots(context)
        try:
            abs_path, root = resolve_path(input.get("path"), roots)
        except ValueError:
            return _error("INVALID_PATH")
        except PermissionError:
            return _error("PATH_NOT_ALLOWED")

        if abs_path.exists() and abs_path.is_dir():
            return _error("INVALID_PATH")

        tool_config = get_tool_config(context, self.name)
        max_bytes = coerce_int(tool_config.get("max_bytes"), DEFAULT_MAX_BYTES)

        content_bytes = content.encode("utf-8")
        if len(content_bytes) > max_bytes:
            return _error("CONTENT_TOO_LARGE")

        create_dirs = input.get("create_dirs", True)
        if bool(create_dirs):
            abs_path.parent.mkdir(parents=True, exist_ok=True)
        elif not abs_path.parent.exists():
            return _error("MISSING_PARENT")

        created = not abs_path.exists()
        mode = None
        if abs_path.exists():
            try:
                mode = abs_path.stat().st_mode
            except OSError:
                mode = None

        try:
            atomic_write(abs_path, content_bytes, mode=mode)
        except OSError:
            return _error("WRITE_FAILED")

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


def _error(code: str) -> ToolResult:
    return ToolResult(success=False, output={}, error=code, evidence=[])

