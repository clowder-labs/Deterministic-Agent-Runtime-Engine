"""Tool domain: tool provider interface for BaseContext."""

from dare_framework3_4.tool.component import IToolProvider
from dare_framework3_4.tool.types import ToolResult, Evidence

__all__ = [
    "IToolProvider",
    "ToolResult",
    "Evidence",
]
