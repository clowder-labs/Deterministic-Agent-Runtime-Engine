"""Native tool provider implementation.

Manages local ITool instances and exposes them as a tool source.
"""

from __future__ import annotations

from dare_framework.tool.kernel import ITool, IToolProvider


class NativeToolProvider(IToolProvider):
    """Tool source for locally registered ITool implementations."""

    def __init__(self, *, tools: list[ITool] | None = None) -> None:
        self._tools: dict[str, ITool] = {}
        if tools:
            for tool in tools:
                self.register_tool(tool)

    def register_tool(self, tool: ITool) -> None:
        """Register a tool.

        Args:
            tool: The tool to register.

        Raises:
            ValueError: If tool with same name already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool by name.

        Args:
            name: The tool name to unregister.

        Returns:
            True if tool was found and removed, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> ITool | None:
        """Get a tool by name.

        Args:
            name: The tool name.

        Returns:
            The tool or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[ITool]:
        """Return registered tools as tool instances."""
        return list(self._tools.values())


__all__ = ["NativeToolProvider"]
