"""Shared utilities used across the framework."""

from dare_framework2.utils.ids import generate_id
from dare_framework2.utils.errors import (
    ToolError,
    ToolNotFoundError,
    ToolAccessDenied,
    ApprovalRequired,
)

__all__ = [
    "generate_id",
    "ToolError",
    "ToolNotFoundError",
    "ToolAccessDenied",
    "ApprovalRequired",
]
