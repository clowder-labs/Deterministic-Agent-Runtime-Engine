"""Context domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from dare_framework3.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    Prompt,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
    Budget,
    ResourceType,
)

if TYPE_CHECKING:
    from dare_framework3.plan.types import Task


class IContextManager(Protocol):
    """Context engineering responsibility owner."""

    def open_session(self, task: "Task") -> SessionContext:
        ...

    async def assemble(
        self,
        stage: ContextStage,
        state: RuntimeStateView,
    ) -> AssembledContext:
        ...

    async def retrieve(
        self,
        query: str,
        *,
        budget: Budget,
    ) -> RetrievedContext:
        ...

    async def ensure_index(self, scope: str) -> IndexStatus:
        ...

    async def compress(
        self,
        context: AssembledContext,
        *,
        budget: Budget,
    ) -> AssembledContext:
        ...

    async def route(self, packet: ContextPacket, target: str) -> None:
        ...


class IContextStrategy(Protocol):
    """Strategy for building prompts from assembled context."""

    async def build_prompt(self, assembled: AssembledContext) -> Prompt:
        ...


class IResourceManager(Protocol):
    """Unified budget model and accounting."""

    def get_budget(self, scope: str) -> Budget:
        ...

    def acquire(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        ...

    def record(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        ...

    def check_limit(self, *, scope: str) -> None:
        ...


__all__ = ["IContextManager", "IContextStrategy", "IResourceManager"]
