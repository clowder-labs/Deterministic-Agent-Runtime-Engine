"""Stable action identifiers for transport-driven deterministic requests."""

from __future__ import annotations

from enum import StrEnum


class ResourceAction(StrEnum):
    """Built-in action identifiers.

    Values are stable strings in `resource:action` form.
    """

    CONFIG_GET = "config:get"
    ACTIONS_LIST = "actions:list"
    TOOLS_LIST = "tools:list"
    APPROVALS_LIST = "approvals:list"
    APPROVALS_POLL = "approvals:poll"
    APPROVALS_GRANT = "approvals:grant"
    APPROVALS_DENY = "approvals:deny"
    APPROVALS_REVOKE = "approvals:revoke"
    MCP_LIST = "mcp:list"
    MCP_RELOAD = "mcp:reload"
    MCP_SHOW_TOOL = "mcp:show-tool"
    SKILLS_LIST = "skills:list"
    MODEL_GET = "model:get"
    GUIDE_INJECT = "guide:inject"
    GUIDE_LIST = "guide:list"
    GUIDE_CLEAR = "guide:clear"

    @classmethod
    def value_of(cls, raw: str) -> ResourceAction | None:
        """Resolve an action id string to enum value, or return None when unknown."""
        normalized = raw.strip()
        if not normalized:
            return None
        try:
            return cls(normalized)
        except ValueError:
            return None

    @property
    def resource(self) -> str:
        resource, _, _action = self.value.partition(":")
        return resource

    @property
    def action(self) -> str:
        _resource, _, action = self.value.partition(":")
        return action

__all__ = ["ResourceAction"]
