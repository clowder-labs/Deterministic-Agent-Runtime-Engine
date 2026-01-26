"""Skill contracts (v2).

Skills are optional pluggable capabilities that can be injected into planning/execution.
For the MVP, we keep the surface similar to tools: input + RunContext -> ToolResult.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolResult
from dare_framework.builder.plugin_system.configurable_component import IConfigurableComponent


@runtime_checkable
class ISkill(IConfigurableComponent, Protocol):
    """A pluggable skill capability (Layer 2)."""

    @property
    def name(self) -> str:
        """Unique skill identifier."""

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        """Execute the skill within a run context."""
