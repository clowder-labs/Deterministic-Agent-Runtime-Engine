"""Compatibility NoOpTool wrapper."""

from __future__ import annotations

from dare_framework3_4.tool._internal.noop_tool import NoopTool as _NoopTool


class NoOpTool(_NoopTool):
    """Alias for NoopTool (capitalization compatibility)."""


__all__ = ["NoOpTool"]
