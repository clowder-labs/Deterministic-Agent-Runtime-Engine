from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from dare_framework.contracts.evidence import Evidence
from dare_framework.contracts.ids import generator_id
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolResult, ToolType
from dare_framework.components.plugin_system.component_type import ComponentType
from ..base_component import ConfigurableComponent


class RunCommandTool(ConfigurableComponent):
    component_type = ComponentType.TOOL

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "Execute a shell command within an allowed workspace root."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
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
            },
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.NON_IDEMPOTENT_EFFECT

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

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        command = input.get("command")
        if not isinstance(command, str) or not command.strip():
            return _error_result("command is required")

        roots = _resolve_workspace_roots(context)
        cwd = _resolve_cwd(input.get("cwd"), roots)
        if cwd is None or not _is_allowed_path(cwd, roots):
            return _error_result("working directory is not within workspace roots")

        timeout = _parse_timeout(input.get("timeout_seconds"), self.timeout_seconds)

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
            return _error_result("command timed out")
        except Exception as exc:  # noqa: BLE001
            return _error_result(str(exc))

        result = ToolResult(
            success=proc.returncode == 0,
            output={
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode,
            },
            error=None if proc.returncode == 0 else "command failed",
            evidence=[Evidence(evidence_id=generator_id("evidence"), kind="command", payload={"cwd": str(cwd)})],
        )
        return result


def _resolve_workspace_roots(context: RunContext) -> list[Path]:
    if context.config and context.config.workspace_roots:
        return [Path(root).expanduser().resolve() for root in context.config.workspace_roots]
    return [Path.cwd().resolve()]


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
            if str(path).startswith(str(root)):
                return True
    return False


def _parse_timeout(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _error_result(message: str) -> ToolResult:
    return ToolResult(success=False, output={}, error=message, evidence=[])
