"""Kernel budget protocols (v2)."""

from __future__ import annotations

from typing import Protocol

from dare_framework.execution.impl.budget.models import Budget, ResourceType


class IResourceManager(Protocol):
    """Unified budget model and accounting (v2.0)."""

    def get_budget(self, scope: str) -> Budget: ...

    def acquire(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        """Reserve resources for a scope; raises ResourceExhausted on failure."""

    def record(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        """Record consumption for audit and feedback loops."""

    def check_limit(self, *, scope: str) -> None:
        """Raise ResourceExhausted if the scope is over budget."""
