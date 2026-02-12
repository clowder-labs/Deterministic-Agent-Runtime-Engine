"""Search code tool implementation."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Iterable, TypedDict

from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
from dare_framework.tool.errors import ToolError
from dare_framework.tool._internal.file_utils import (
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
from dare_framework.infra.ids import generate_id
from dare_framework.tool.types import (
    CapabilityKind,
    Evidence,
    RunContext,
    ToolResult,
    ToolType,
)


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
        return 20

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        return [{"type": "search_results", "produces": {"pattern": "*"}}]

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
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        max_results: int | None = None,
        context_lines: int = 2,
    ) -> ToolResult[SearchCodeOutput]:
        """Search files for regex matches.

        Args:
            run_context: Runtime invocation context.
            pattern: Regex pattern to search.
            path: Directory or file path to search under.
            file_pattern: Glob pattern used to filter candidate files.
            max_results: Optional maximum number of matches to return.
            context_lines: Number of lines of context to include around matches.

        Returns:
            Search result payload with matches and truncation metadata.
        """
        try:
            payload: dict[str, Any] = {
                "pattern": pattern,
                "path": path,
                "file_pattern": file_pattern,
                "context_lines": context_lines,
            }
            if max_results is not None:
                payload["max_results"] = max_results
            return _execute_search(payload, run_context)
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


class SearchCodeMatch(TypedDict):
    file: str
    line: int
    content: str
    context_before: list[str]
    context_after: list[str]


class SearchCodeOutput(TypedDict):
    matches: list[SearchCodeMatch]
    total_matches: int
    truncated: bool
