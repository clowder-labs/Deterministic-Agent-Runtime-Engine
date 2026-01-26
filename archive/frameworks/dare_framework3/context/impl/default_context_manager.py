"""Default context manager implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework3.context.component import IContextManager
from dare_framework3.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
)
from dare_framework3.model.types import Message

if TYPE_CHECKING:
    from dare_framework3.memory.component import IMemory
    from dare_framework3.plan.types import Task
    from dare_framework3.context.types import Budget


class DefaultContextManager(IContextManager):
    """Minimal context manager supporting PLAN/EXECUTE assembly.
    
    This is an MVP implementation that provides basic context assembly
    for the plan and execute stages. More sophisticated context engineering
    can be added in future implementations.
    
    Args:
        memory: Optional memory component for retrieval operations
    """

    def __init__(self, *, memory: "IMemory | None" = None) -> None:
        self._memory = memory

    def open_session(self, task: "Task") -> SessionContext:
        """Open a session for the given task."""
        return SessionContext(
            user_input=task.description,
            metadata={"task_id": task.task_id},
        )

    async def assemble(
        self,
        stage: ContextStage,
        state: RuntimeStateView,
    ) -> AssembledContext:
        """Assemble context for the given stage.
        
        MVP implementation provides minimal system/user messages.
        """
        user_content = (
            state.data.get("user_input")
            or state.data.get("task_description")
            or ""
        )
        messages = [
            Message(role="system", content=f"DARE Kernel v3.0 stage={stage.value}"),
            Message(role="user", content=str(user_content)),
        ]
        metadata: dict[str, Any] = {
            "task_id": state.task_id,
            "run_id": state.run_id,
            "milestone_id": state.milestone_id,
            "stage": stage.value,
        }
        return AssembledContext(messages=messages, metadata=metadata)

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget",
    ) -> RetrievedContext:
        """Retrieve context from memory if available."""
        if self._memory is None:
            return RetrievedContext(items=[])
        items = await self._memory.retrieve(query, budget=budget)
        return RetrievedContext(items=list(items))

    async def ensure_index(self, scope: str) -> IndexStatus:
        """MVP: Always report index as ready."""
        return IndexStatus(ready=True, details={"scope": scope, "mode": "noop"})

    async def compress(
        self,
        context: AssembledContext,
        *,
        budget: "Budget",
    ) -> AssembledContext:
        """MVP: Return context unchanged (no compression)."""
        return context

    async def route(self, packet: ContextPacket, target: str) -> None:
        """MVP: No-op routing."""
        pass
