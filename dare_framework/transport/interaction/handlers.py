"""Action handler contracts for deterministic interaction routing."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.transport.interaction.resource_action import ResourceAction


class IActionHandler(Protocol):
    """Handle one or more deterministic resource actions."""

    def supports(self) -> set[ResourceAction]:
        """Return the set of ResourceAction values supported by this handler."""

    async def invoke(
        self,
        action: ResourceAction,
        **params: Any,
    ) -> Any:
        """Handle the action and return a JSON-serializable result."""


__all__ = ["IActionHandler"]
