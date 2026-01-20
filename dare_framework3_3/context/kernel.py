"""Context domain kernel interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from dare_framework3_3.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
    Budget,
    ResourceType,
)

if TYPE_CHECKING:
    from dare_framework3_3.plan.types import Task


class IContextManager(Protocol):
    """[Kernel] Owns context assembly across agent stages.

    Usage: Called by the agent loop to open sessions, assemble prompts,
    and manage retrieval/compression for each execution stage.
    """

    def open_session(self, task: "Task") -> SessionContext:
        """[Kernel] Start a session-scoped context.

        Usage: Invoked once per task before stage execution begins.
        """
        ...

    async def assemble(
        self,
        stage: ContextStage,
        state: RuntimeStateView,
    ) -> AssembledContext:
        """[Kernel] Assemble context for a specific stage.

        Usage: Called by the agent to build the prompt context window.
        """
        ...

    async def retrieve(
        self,
        query: str,
        *,
        budget: Budget,
    ) -> RetrievedContext:
        """[Kernel] Retrieve context items under a budget.

        Usage: Called by planners/strategies to fetch relevant memory.
        """
        ...

    async def ensure_index(self, scope: str) -> IndexStatus:
        """[Kernel] Ensure retrieval index readiness.

        Usage: Called before retrieval to verify indexing status.
        """
        ...

    async def compress(
        self,
        context: AssembledContext,
        *,
        budget: Budget,
    ) -> AssembledContext:
        """[Kernel] Compress context to fit budget constraints.

        Usage: Called before model invocation when context is too large.
        """
        ...

    async def route(self, packet: ContextPacket, target: str) -> None:
        """[Kernel] Route context packets between scopes/agents.

        Usage: Called for cross-agent or cross-window context transfers.
        """
        ...


class IResourceManager(Protocol):
    """[Kernel] Budget accounting and resource enforcement.

    Usage: Called by the agent loop and tools to enforce budgets for
    time, tokens, tool calls, and cost.
    """

    def get_budget(self, scope: str) -> Budget:
        """[Kernel] Return the budget for a scope.

        Usage: Called before resource acquisition to determine limits.
        """
        ...

    def acquire(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        """[Kernel] Acquire resource and enforce limits.

        Usage: Called before resource consumption (e.g., tool call).
        """
        ...

    def record(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        """[Kernel] Record resource usage without enforcement.

        Usage: Called after usage when enforcement is handled separately.
        """
        ...

    def check_limit(self, *, scope: str) -> None:
        """[Kernel] Validate resource usage against the budget.

        Usage: Called to fail fast if a scope exceeds its limits.
        """
        ...


__all__ = ["IContextManager", "IResourceManager"]
