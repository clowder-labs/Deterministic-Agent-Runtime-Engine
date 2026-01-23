"""Search code tool implementation."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Iterable

from dare_framework3_4.security.types import RiskLevel
from dare_framework3_4.tool.component import ITool
from dare_framework3_4.tool.errors import ToolError
from dare_framework3_4.tool.internal.file_utils import (
    DEFAULT_IGNORE_DIRS,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_RESULTS,
    coerce_int,
    coerce_list,
    get_tool_config,
    relative_to_root,
    resolve_path,
    resolve_workspace_roots,
)
from dare_framework3_4.tool.internal.ids import generate_id
from dare_framework3_4.tool.types import Evidence, RunContext, ToolResult, ToolType


class SearchCodeTool(ITool):
    """Search for a regex pattern across files within the workspace roots."""

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return "Search for a regex pattern across files within the workspace roots."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search"},
                "path": {"type": "string", "description": "Directory or file path"},
                "file_pattern": {"type": "string", "description": "Glob pattern (e.g. *.py)"},
                "max_results": {"type": "integer", "minimum": 1},
                "context_lines": {"type": "integer", "minimum": 0},
            },
            "required": ["pattern"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"},
                            "content": {"type": "string"},
                            "context_before": {"type": "array", "items": {"type": "string"}},
                            "context_after": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "total_matches": {"type": "integer"},
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
        return 20

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        return [{"type": "search_results", "produces": {"pattern": "*"}}]

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        try:
            return _execute_search(input, context)
        except ToolError as exc:
            return _error_result(exc)


def _execute_search(input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
    pattern = input.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ToolError(code="INVALID_PATTERN", message="pattern is required", retryable=False)
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ToolError(code="INVALID_PATTERN", message="pattern is not a valid regex") from exc

    tool_config = get_tool_config(context, "search_code")
    max_results_guardrail = coerce_int(tool_config.get("max_results"), DEFAULT_MAX_RESULTS)
    max_file_bytes = coerce_int(tool_config.get("max_file_bytes"), DEFAULT_MAX_BYTES)
    ignore_dirs = set(coerce_list(tool_config.get("ignore_dirs"), DEFAULT_IGNORE_DIRS))

    requested_max = coerce_int(input.get("max_results"), max_results_guardrail)
    max_results = min(requested_max, max_results_guardrail)
    context_lines = coerce_int(input.get("context_lines"), 2, min_value=0)

    roots = resolve_workspace_roots(context)
    search_path_value = input.get("path", ".")
    search_path, root = resolve_path(search_path_value, roots)

    if not search_path.exists():
        raise ToolError(code="SEARCH_PATH_NOT_FOUND", message="search path not found", retryable=False)
    if not search_path.is_dir() and not search_path.is_file():
        raise ToolError(code="INVALID_PATH", message="search path must be file or directory")

    file_pattern = input.get("file_pattern", "*")
    if not isinstance(file_pattern, str) or not file_pattern:
        file_pattern = "*"

    matches: list[dict[str, Any]] = []
    truncated = False

    for file_path in _iter_files(search_path, file_pattern, ignore_dirs):
        resolved = file_path.resolve()
        if not resolved.exists() or not resolved.is_file():
            continue
        try:
            size_bytes = resolved.stat().st_size
        except OSError:
            continue
        if size_bytes > max_file_bytes:
            continue
        if not _is_under_root(resolved, root):
            continue
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            if regex.search(line):
                matches.append(
                    {
                        "file": relative_to_root(resolved, root),
                        "line": idx + 1,
                        "content": line,
                        "context_before": lines[max(0, idx - context_lines):idx],
                        "context_after": lines[idx + 1:idx + 1 + context_lines],
                    }
                )
                if len(matches) >= max_results:
                    truncated = True
                    break
        if truncated:
            break

    return ToolResult(
        success=True,
        output={
            "matches": matches,
            "total_matches": len(matches),
            "truncated": truncated,
        },
        evidence=[
            Evidence(
                evidence_id=generate_id("evidence"),
                kind="search_matches",
                payload={"pattern": pattern, "match_count": len(matches)},
            )
        ],
    )


def _iter_files(search_path: Path, file_pattern: str, ignore_dirs: set[str]) -> Iterable[Path]:
    if search_path.is_file():
        if fnmatch.fnmatch(search_path.name, file_pattern):
            yield search_path
        return
    if not search_path.is_dir():
        return
    for root, dirs, files in os.walk(search_path, topdown=True, followlinks=False):
        dirs[:] = [d for d in sorted(dirs) if d not in ignore_dirs]
        for filename in sorted(files):
            if fnmatch.fnmatch(filename, file_pattern):
                yield Path(root) / filename


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        return path.is_relative_to(root)
    except AttributeError:
        root_str = str(root)
        path_str = str(path)
        if path_str == root_str:
            return True
        return path_str.startswith(root_str.rstrip(os.sep) + os.sep)


def _error_result(error: ToolError) -> ToolResult:
    return ToolResult(
        success=False,
        output={"code": error.code},
        error=error.message,
        evidence=[],
    )
