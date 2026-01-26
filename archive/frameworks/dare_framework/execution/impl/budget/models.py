"""Kernel budget models (v2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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

