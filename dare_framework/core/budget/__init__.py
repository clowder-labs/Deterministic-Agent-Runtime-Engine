from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ResourceType(Enum):
    """Canonical resource types used by the Kernel budget model (v2.0)."""

    TOKENS = "tokens"
    COST = "cost"
    TIME_SECONDS = "time_seconds"
    TOOL_CALLS = "tool_calls"


@dataclass(frozen=True)
class Budget:
    """Coarse-grained budgets for a scope or envelope (v2.0).

    The initial implementation is allowed to enforce only a subset (e.g. tool calls / time),
    but the type surface must exist for future refinement.
    """

    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None


class ResourceExhausted(RuntimeError):
    """Raised when a budget limit is exceeded."""


class IResourceManager(Protocol):
    """Unified budget model and accounting (v2.0)."""

    def get_budget(self, scope: str) -> Budget: ...

    def acquire(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        """Reserve resources for a scope; raises ResourceExhausted on failure."""

    def record(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        """Record consumption for audit and feedback loops."""

    def check_limit(self, *, scope: str) -> None:
        """Raise ResourceExhausted if the scope is over budget."""
