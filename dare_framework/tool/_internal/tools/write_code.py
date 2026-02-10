"""Write code tool implementation."""

from __future__ import annotations

from dare_framework.tool._internal.tools.write_file import WriteFileTool


class WriteCodeTool(WriteFileTool):
    """Compatibility alias for code-oriented write operations."""

    @property
    def name(self) -> str:
        return "write_code"

    @property
    def description(self) -> str:
        return "Write source code content to a file within the workspace roots."

