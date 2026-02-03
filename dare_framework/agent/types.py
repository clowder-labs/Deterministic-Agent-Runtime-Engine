"""agent domain types.

This domain contains developer-facing agent contracts and (optionally) default
agent implementations under `_internal/`.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeAlias

from dare_framework.plan.types import SessionSummary

AgentDeps: TypeAlias = Any


class ISessionSummaryStore(Protocol):
    """Optional persistence hook for SessionSummary objects."""

    async def save(self, summary: SessionSummary) -> None: ...


__all__ = ["AgentDeps", "ISessionSummaryStore"]
