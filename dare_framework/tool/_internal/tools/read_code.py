"""Read code tool implementation."""

from __future__ import annotations

from dare_framework.tool._internal.tools.read_file import ReadFileTool


class ReadCodeTool(ReadFileTool):
    """Compatibility alias for code-oriented read operations."""

    @property
    def name(self) -> str:
        return "read_code"

    @property
    def description(self) -> str:
        return "Read source code content from a file within the workspace roots."

