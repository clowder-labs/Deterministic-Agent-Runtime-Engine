"""Tool domain component interfaces.

Defines IToolProvider for BaseContext.tools integration.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IToolProvider(Protocol):
    """[Component] Tool provider interface.

    Usage: Injected into BaseContext.tools.
    Provides tool listing capability for context assembly.

    Note: This is a minimal interface for BaseContext integration.
    Full tool execution interfaces (ITool, IToolGateway, etc.) remain
    in the existing tool domain implementation.
    """

    def list_tools(self) -> list[dict[str, Any]]:
        """Get available tool definitions in LLM-compatible format.

        Returns:
            List of tool definitions with name, description, parameters, etc.
        """
        ...


__all__ = ["IToolProvider"]
