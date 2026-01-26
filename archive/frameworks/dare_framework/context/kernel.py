"""Kernel context protocols (v2)."""

from __future__ import annotations

from typing import Protocol

from dare_framework.execution.types import Budget
from dare_framework.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
)


class IContextManager(Protocol):
    """Context engineering responsibility owner (v2.0)."""

    def open_session(self, task: "Task") -> SessionContext: ...

    async def assemble(self, stage: ContextStage, state: RuntimeStateView) -> AssembledContext: ...

    async def retrieve(self, query: str, *, budget: Budget) -> RetrievedContext: ...

    async def ensure_index(self, scope: str) -> IndexStatus: ...

    async def compress(self, context: AssembledContext, *, budget: Budget) -> AssembledContext: ...

    async def route(self, packet: ContextPacket, target: str) -> None: ...

