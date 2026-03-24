"""Lazy exports for tool facade defaults."""

from __future__ import annotations

from typing import Any

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "ToolManager": ("dare_framework.tool.tool_manager", "ToolManager"),
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
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        module_name, attr_name = _LAZY_ATTRS[name]
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

