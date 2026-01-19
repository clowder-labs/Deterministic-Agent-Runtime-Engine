from __future__ import annotations

from typing import Any

from dare_framework.contracts.memory import IMemory
from dare_framework.contracts.model import Message
from dare_framework.core.budget import Budget
from dare_framework.core.context import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IContextManager,
    IndexStatus,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
)
from dare_framework.core.plan.task import Task


class DefaultContextManager(IContextManager):
    """Minimal context manager that supports PLAN/EXECUTE assembly (MVP)."""

    def __init__(self, *, memory: IMemory | None = None) -> None:
        # Memory is optional in early v2 milestones; keep the context manager usable without it.
        self._memory = memory

    def open_session(self, task: Task) -> SessionContext:
        return SessionContext(user_input=task.description, metadata={"task_id": task.task_id})

    async def assemble(self, stage: ContextStage, state: RuntimeStateView) -> AssembledContext:
        # MVP prompt: provide stage and the minimal user/task payload; richer context engineering can be added later.
        user_content = state.data.get("user_input") or state.data.get("task_description") or ""
        messages = [
            Message(role="system", content=f"DARE Kernel v2.0 stage={stage.value}"),
            Message(role="user", content=str(user_content)),
        ]
        metadata: dict[str, Any] = {
            "task_id": state.task_id,
            "run_id": state.run_id,
            "milestone_id": state.milestone_id,
            "stage": stage.value,
        }
        return AssembledContext(messages=messages, metadata=metadata)

    async def retrieve(self, query: str, *, budget: Budget) -> RetrievedContext:
        if self._memory is None:
            return RetrievedContext(items=[])
        items = await self._memory.retrieve(query, budget=budget)
        return RetrievedContext(items=list(items))

    async def ensure_index(self, scope: str) -> IndexStatus:
        return IndexStatus(ready=True, details={"scope": scope, "mode": "noop"})

    async def compress(self, context: AssembledContext, *, budget: Budget) -> AssembledContext:
        return context

    async def route(self, packet: ContextPacket, target: str) -> None:
        # Optional v2 capability; MVP is a no-op.
        return None
