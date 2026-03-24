"""Lazy exports for the internal tool package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "AskUserTool",
    "AutoUserInputHandler",
    "CLIUserInputHandler",
    "IUserInputHandler",
    "Checkpoint",
    "DefaultExecutionControl",
    "FileExecutionControl",
    "NativeToolProvider",
    "ToolManager",
    "EchoTool",
    "NoopTool",
    "RunCommandTool",
    "ReadFileTool",
    "SearchCodeTool",
    "WriteFileTool",
    "EditLineTool",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "AskUserTool": ("dare_framework.tool._internal.tools.ask_user", "AskUserTool"),
    "CLIUserInputHandler": (
        "dare_framework.tool._internal.tools.ask_user",
        "CLIUserInputHandler",
    ),
    "AutoUserInputHandler": (
        "dare_framework.tool._internal.tools.ask_user",
        "AutoUserInputHandler",
    ),
    "IUserInputHandler": (
        "dare_framework.tool._internal.tools.ask_user",
        "IUserInputHandler",
    ),
    "Checkpoint": (
        "dare_framework.tool._internal.control.default_execution_control",
        "Checkpoint",
    ),
    "DefaultExecutionControl": (
        "dare_framework.tool._internal.control.default_execution_control",
        "DefaultExecutionControl",
    ),
    "FileExecutionControl": (
        "dare_framework.tool._internal.control.file_execution_control",
        "FileExecutionControl",
    ),
    "NativeToolProvider": (
        "dare_framework.tool._internal.native_tool_provider",
        "NativeToolProvider",
    ),
    "ToolManager": ("dare_framework.tool.tool_manager", "ToolManager"),
    "EchoTool": ("dare_framework.tool._internal.tools.echo_tool", "EchoTool"),
    "NoopTool": ("dare_framework.tool._internal.tools.noop_tool", "NoopTool"),
    "RunCommandTool": ("dare_framework.tool._internal.tools.run_command_tool", "RunCommandTool"),
    "ReadFileTool": ("dare_framework.tool._internal.tools.read_file", "ReadFileTool"),
    "SearchCodeTool": ("dare_framework.tool._internal.tools.search_code", "SearchCodeTool"),
    "WriteFileTool": ("dare_framework.tool._internal.tools.write_file", "WriteFileTool"),
    "EditLineTool": ("dare_framework.tool._internal.tools.edit_line", "EditLineTool"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
