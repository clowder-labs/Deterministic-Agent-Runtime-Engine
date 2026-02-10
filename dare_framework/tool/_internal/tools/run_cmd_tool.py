"""Run command alias tool implementation."""

from __future__ import annotations

from dare_framework.tool._internal.tools.run_command_tool import RunCommandTool


class RunCmdTool(RunCommandTool):
    """Compatibility alias for run_command."""

    @property
    def name(self) -> str:
        return "run_cmd"

    @property
    def description(self) -> str:
        return "Run an arbitrary shell command in the workspace."

