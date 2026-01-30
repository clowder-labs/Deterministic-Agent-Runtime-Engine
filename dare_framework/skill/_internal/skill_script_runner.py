"""Unified tool for executing skill scripts (run_skill_script)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.tool.interfaces import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    Evidence,
    RunContext,
    ToolResult,
    ToolType,
)
from dare_framework.tool._internal.utils.ids import generate_id

if TYPE_CHECKING:
    from dare_framework.skill.interfaces import ISkillStore


class SkillScriptRunner(ITool, IComponent):
    """Unified entry tool: run_skill_script(skill_id, script_name, args).

    LLM calls this tool to execute scripts defined in a skill's scripts/ directory.
    """

    def __init__(self, skill_store: "ISkillStore") -> None:
        self._skill_store = skill_store

    @property
    def name(self) -> str:
        return "run_skill_script"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return (
            "Execute a script from an Agent Skill. "
            "Use when the active skill's instructions require running a specific script. "
            "Provide skill_id (e.g. 'code-review'), script_name (e.g. 'run_linter'), and optional args."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Skill identifier (e.g. 'code-review').",
                },
                "script_name": {
                    "type": "string",
                    "description": "Script name without extension (e.g. 'run_linter').",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of command-line arguments to pass to the script.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "description": "Optional execution timeout in seconds.",
                },
            },
            "required": ["skill_id", "script_name"],
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
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
        return "non_idempotent_effect"

    @property
    def requires_approval(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 60

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.SKILL

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        skill_id = input.get("skill_id")
        script_name = input.get("script_name")
        if not isinstance(skill_id, str) or not skill_id.strip():
            return _error_result("skill_id is required")
        if not isinstance(script_name, str) or not script_name.strip():
            return _error_result("script_name is required")

        skill = self._skill_store.get_skill(skill_id.strip())
        if skill is None:
            return _error_result(f"skill not found: {skill_id}")

        script_path = skill.get_script_path(script_name.strip())
        if script_path is None:
            available = ", ".join(sorted(skill.scripts.keys())) or "(none)"
            return _error_result(
                f"script '{script_name}' not found in skill '{skill_id}'. Available: {available}"
            )

        args_list: list[str] = []
        raw_args = input.get("args")
        if isinstance(raw_args, list):
            args_list = [str(a) for a in raw_args]

        timeout = self.timeout_seconds
        if isinstance(input.get("timeout_seconds"), (int, float)):
            timeout = min(int(input["timeout_seconds"]), 300)

        cwd = str(skill.skill_dir) if skill.skill_dir else None
        argv = _build_argv(script_path, args_list)

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.communicate()
            return _error_result("script execution timed out")
        except Exception as exc:
            return _error_result(str(exc))

        return ToolResult(
            success=proc.returncode == 0,
            output={
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode,
                "skill_id": skill_id,
                "script_name": script_name,
            },
            error=None if proc.returncode == 0 else "script exited with non-zero code",
            evidence=[
                Evidence(
                    evidence_id=generate_id("evidence"),
                    kind="skill_script",
                    payload={"skill_id": skill_id, "script_name": script_name, "path": str(script_path)},
                )
            ],
        )


def _build_argv(script_path: Path, args: list[str]) -> list[str]:
    """Build argv for executing the script. Uses python for .py, sh for .sh, else direct."""
    suffix = script_path.suffix.lower()
    if suffix == ".py":
        return ["python", str(script_path), *args]
    if suffix in (".sh", ".bash"):
        return ["sh", str(script_path), *args]
    return [str(script_path), *args]


def _error_result(message: str) -> ToolResult:
    return ToolResult(success=False, output={}, error=message, evidence=[])


__all__ = ["SkillScriptRunner"]
