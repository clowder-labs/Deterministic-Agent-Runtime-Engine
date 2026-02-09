"""agent domain types.

This domain contains developer-facing agent contracts and default agent
implementations under `dare_framework/agent`.
"""

from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from dare_framework.plan.types import SessionSummary

AgentDeps: TypeAlias = Any


class ISessionSummaryStore(Protocol):
    """Persistent store for session summaries."""

    async def save(self, summary: SessionSummary) -> None:
        """Persist a session summary."""
        ...


__all__ = ["AgentDeps", "ISessionSummaryStore"]
