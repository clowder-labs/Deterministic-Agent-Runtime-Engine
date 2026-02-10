"""Run command tool implementation."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from dare_framework.tool.kernel import ITool
from dare_framework.tool.errors import ToolError
from dare_framework.tool._internal.file_utils import (
    DEFAULT_MAX_BYTES,
    coerce_int,
    get_tool_config,
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


class RunCommandTool(ITool):
    """Execute a shell command within an allowed workspace root."""

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return (
            "Run an arbitrary shell command in the workspace (e.g. git, npm, pip, ls). "
            "Use for general terminal commands. Do NOT use for skill scripts—use run_skill_script(skill_id, script_name) instead."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Full shell command to run (e.g. 'git status', 'npm install'). Not for skill scripts—use run_skill_script for those.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory; must be inside workspace root.",
                },
                "timeout_seconds": {"type": "integer", "minimum": 1},
            },
            "required": ["command"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"},
                "stdout_truncated": {"type": "boolean"},
                "stderr_truncated": {"type": "boolean"},
            },
        }

    @property
    def risk_level(self) -> str:
        return "non_idempotent_effect"

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def requires_approval(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        try:
            return await _execute_command(input, context, self.timeout_seconds)
        except ToolError as exc:
            return _error_result(exc)


async def _execute_command(
    input: dict[str, Any],
    context: RunContext[Any],
    default_timeout_seconds: int,
) -> ToolResult:
    command = input.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ToolError(code="INVALID_COMMAND", message="command is required", retryable=False)

    roots = resolve_workspace_roots(context)
    cwd = _resolve_cwd(input.get("cwd"), roots)
    _validate_cwd(cwd, roots)

    tool_config = get_tool_config(context, "run_command")
    max_timeout_seconds = coerce_int(
        tool_config.get("max_timeout_seconds"),
        default_timeout_seconds,
    )
    timeout = _parse_timeout(
        value=input.get("timeout_seconds"),
        fallback=default_timeout_seconds,
        max_timeout=max_timeout_seconds,
    )
    max_output_bytes = coerce_int(tool_config.get("max_output_bytes"), DEFAULT_MAX_BYTES)

    proc: asyncio.subprocess.Process | None = None
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        if proc and proc.returncode is None:
            proc.kill()
            await proc.communicate()
        raise ToolError(code="COMMAND_TIMED_OUT", message="command timed out", retryable=True) from None
    except Exception as exc:  # noqa: BLE001
        raise ToolError(code="EXECUTION_FAILED", message=str(exc), retryable=False) from exc

    stdout_text, stdout_truncated = _truncate_output(stdout, max_output_bytes)
    stderr_text, stderr_truncated = _truncate_output(stderr, max_output_bytes)

    failed = proc.returncode != 0
    output: dict[str, Any] = {
        "stdout": stdout_text,
        "stderr": stderr_text,
        "exit_code": proc.returncode,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }
    if failed:
        output["code"] = "COMMAND_FAILED"
    return ToolResult(
        success=not failed,
        output=output,
        error=None if not failed else "command failed",
        evidence=[
            Evidence(
                evidence_id=generate_id("evidence"),
                kind="command",
                payload={"cwd": str(cwd), "exit_code": proc.returncode},
            )
        ],
    )


def _resolve_cwd(cwd: Any, roots: list[Path]) -> Path | None:
    if cwd is None:
        return roots[0] if roots else None
    path = Path(str(cwd)).expanduser()
    if not path.is_absolute():
        path = roots[0] / path
    return path.resolve()


def _validate_cwd(cwd: Path | None, roots: list[Path]) -> None:
    if cwd is None or not roots:
        raise ToolError(code="INVALID_CWD", message="working directory is required", retryable=False)
    if not _is_allowed_path(cwd, roots):
        raise ToolError(
            code="INVALID_CWD",
            message="working directory is not within workspace roots",
            retryable=False,
        )
    if not cwd.exists():
        raise ToolError(code="INVALID_CWD", message="working directory does not exist", retryable=False)
    if not cwd.is_dir():
        raise ToolError(code="INVALID_CWD", message="working directory is not a directory", retryable=False)


def _is_allowed_path(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            if path.is_relative_to(root):
                return True
        except AttributeError:
            root_str = str(root)
            normalized_root = root_str.rstrip(os.sep)
            path_str = str(path)
            if path_str == root_str or path_str.startswith(normalized_root + os.sep):
                return True
    return False


def _parse_timeout(value: Any, fallback: int, max_timeout: int) -> int:
    parsed = coerce_int(value, fallback)
    return min(parsed, max(max_timeout, 1))


def _truncate_output(payload: bytes, max_output_bytes: int) -> tuple[str, bool]:
    if len(payload) <= max_output_bytes:
        return payload.decode("utf-8", errors="replace"), False
    suffix = b"\n...[truncated]"
    if max_output_bytes <= len(suffix):
        clipped = payload[:max_output_bytes]
    else:
        clipped = payload[: max_output_bytes - len(suffix)] + suffix
    return clipped.decode("utf-8", errors="replace"), True


def _error_result(error: ToolError) -> ToolResult:
    return ToolResult(
        success=False,
        output={"code": error.code},
        error=error.message,
        evidence=[],
    )
