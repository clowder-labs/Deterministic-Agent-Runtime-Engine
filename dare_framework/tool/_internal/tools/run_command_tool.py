"""Run command tool implementation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, TypedDict

from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
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

    # noinspection PyMethodOverriding
    async def execute(
        self,
        run_context: RunContext[Any] | dict[str, Any],
        command: str | RunContext[Any],
        cwd: str | None = None,
        timeout_seconds: int | None = None,
    ) -> ToolResult[RunCommandOutput]:
        """Run a shell command inside workspace roots.

        Args:
            run_context: Runtime invocation context.
            command: Full shell command to run.
            cwd: Optional working directory; must remain under workspace roots.
            timeout_seconds: Optional command timeout override in seconds.

        Returns:
            Command execution output including stdout, stderr, and exit code.
        """
        normalized = _normalize_execute_args(
            run_context=run_context,
            command=command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        if isinstance(normalized, ToolResult):
            return normalized
        run_context, command, cwd, timeout_seconds = normalized

        if not isinstance(command, str) or not command.strip():
            return _error_result("command is required", code="INVALID_COMMAND")

        roots = resolve_workspace_roots(run_context)
        resolved_cwd = _resolve_cwd(cwd, roots)
        if (
            resolved_cwd is None
            or not _is_allowed_path(resolved_cwd, roots)
            or not resolved_cwd.exists()
            or not resolved_cwd.is_dir()
        ):
            return _error_result("working directory is not within workspace roots", code="INVALID_CWD")

        timeout = _parse_timeout(timeout_seconds, self.timeout_seconds)
        tool_config = get_tool_config(run_context, self.name)
        max_output_bytes = coerce_int(tool_config.get("max_output_bytes"), DEFAULT_MAX_BYTES)

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(resolved_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.communicate()
            return _error_result("command timed out", code="COMMAND_TIMEOUT")
        except Exception as exc:  # noqa: BLE001
            return _error_result(str(exc), code="COMMAND_EXEC_FAILED")

        stdout_text, stdout_truncated = _truncate_text(
            stdout.decode("utf-8", errors="replace"),
            max_output_bytes,
        )
        stderr_text, stderr_truncated = _truncate_text(
            stderr.decode("utf-8", errors="replace"),
            max_output_bytes,
        )

        return ToolResult(
            success=proc.returncode == 0,
            output={
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": proc.returncode,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            },
            error=None if proc.returncode == 0 else "command failed",
            evidence=[
                Evidence(
                    evidence_id=generate_id("evidence"),
                    kind="command",
                    payload={"cwd": str(resolved_cwd)},
                )
            ],
        )


def _normalize_execute_args(
    *,
    run_context: RunContext[Any] | dict[str, Any],
    command: str | RunContext[Any],
    cwd: str | None,
    timeout_seconds: int | None,
) -> (
    tuple[RunContext[Any], str, str | None, int | None]
    | ToolResult
):
    """Support both v4 keyword style and legacy positional input/context style."""

    if isinstance(run_context, dict):
        if not isinstance(command, RunContext):
            return _error_result("run context is required", code="INVALID_CONTEXT")
        input_payload = run_context
        parsed_command = input_payload.get("command")
        parsed_cwd = input_payload.get("cwd", cwd)
        parsed_timeout = input_payload.get("timeout_seconds", timeout_seconds)
        return command, parsed_command, parsed_cwd, parsed_timeout
    if isinstance(command, RunContext):
        return _error_result("command is required", code="INVALID_COMMAND")
    return run_context, command, cwd, timeout_seconds


def _resolve_cwd(cwd: Any, roots: list[Path]) -> Path | None:
    if cwd is None:
        return roots[0] if roots else None
    path = Path(str(cwd)).expanduser()
    if not path.is_absolute():
        path = roots[0] / path
    return path.resolve()


def _is_allowed_path(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            if path.is_relative_to(root):
                return True
        except AttributeError:
            root_str = str(root)
            if str(path) == root_str or str(path).startswith(root_str.rstrip("/") + "/"):
                return True
    return False


def _parse_timeout(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _truncate_text(value: str, max_bytes: int) -> tuple[str, bool]:
    raw = value.encode("utf-8")
    if len(raw) <= max_bytes:
        return value, False
    clipped = raw[:max_bytes]
    text = clipped.decode("utf-8", errors="ignore")
    # Guard against edge-case decoder behavior around boundary bytes.
    while len(text.encode("utf-8")) > max_bytes:
        text = text[:-1]
    return text, True


def _error_result(message: str, *, code: str) -> ToolResult:
    return ToolResult(success=False, output={"code": code}, error=message, evidence=[])


class RunCommandOutput(TypedDict):
    stdout: str
    stderr: str
    exit_code: int
    stdout_truncated: bool
    stderr_truncated: bool
