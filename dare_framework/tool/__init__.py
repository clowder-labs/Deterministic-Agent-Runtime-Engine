"""tool domain facade."""

from __future__ import annotations

from typing import Any

from dare_framework.tool.interfaces import IExecutionControl
from dare_framework.tool.kernel import ITool, IToolGateway, IToolManager, IToolProvider
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    Evidence,
    ExecutionSignal,
    InvocationContext,
    ProviderStatus,
    RiskLevelName,
    RunContext,
    ToolDefinition,
    ToolErrorRecord,
    ToolResult,
    ToolSchema,
    ToolType,
)

__all__ = [
    # Types
    "CapabilityDescriptor",
    "CapabilityKind",
    "CapabilityMetadata",
    "CapabilityType",
    "Evidence",
    "ExecutionSignal",
    "InvocationContext",
    "ProviderStatus",
    "RiskLevelName",
    "RunContext",
    "ToolDefinition",
    "ToolErrorRecord",
    "ToolResult",
    "ToolSchema",
    "ToolType",
    # Kernel interfaces
    "IToolGateway",
    "IToolManager",
    # Pluggable interfaces
    "IExecutionControl",
    "ITool",
    "IToolProvider",
    # Supported defaults
    "ToolManager",
    # Built-in ask_user
    "AskUserTool",
    "CLIUserInputHandler",
    "IUserInputHandler",
]


_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "ToolManager": ("dare_framework.tool.tool_manager", "ToolManager"),
    "AskUserTool": ("dare_framework.tool._internal.tools.ask_user", "AskUserTool"),
    "CLIUserInputHandler": ("dare_framework.tool._internal.tools.ask_user", "CLIUserInputHandler"),
    "IUserInputHandler": ("dare_framework.tool._internal.tools.ask_user", "IUserInputHandler"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        module_name, attr_name = _LAZY_ATTRS[name]
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
