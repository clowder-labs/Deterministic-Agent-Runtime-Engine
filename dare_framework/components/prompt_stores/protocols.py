"""Prompt store component contracts (v2).

This is intentionally minimal. The architecture expects prompt stores to be a
Layer 2 capability used by context engineering (via `IContextManager` and/or
context strategies).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework.components.plugin_system.configurable_component import IConfigurableComponent


@runtime_checkable
class IPromptStore(IConfigurableComponent, Protocol):
    """Retrieves prompt templates/snippets by id."""

    async def get(self, prompt_id: str) -> str | None: ...

