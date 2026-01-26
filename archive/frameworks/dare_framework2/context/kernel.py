"""Context domain kernel interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from dare_framework2.context.types import (
    AssembledContext,
    ContextPacket,
    ContextStage,
    IndexStatus,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
)

if TYPE_CHECKING:
    from dare_framework2.plan.types import Task
    from dare_framework2.execution.types import Budget


class IContextManager(Protocol):
    """Context engineering responsibility owner.
    
    The central interface for all context engineering operations.
    Decides what information enters the LLM's context window and
    provides explainable attribution for included content.
    """

    def open_session(self, task: "Task") -> SessionContext:
        """Open a new session for the given task.
        
        Args:
            task: The task to create a session for
            
        Returns:
            A SessionContext for tracking session state
        """
        ...

    async def assemble(
        self,
        stage: ContextStage,
        state: RuntimeStateView,
    ) -> AssembledContext:
        """Assemble context for the given stage.
        
        Combines system instructions, tool schemas, relevant memories,
        and other context appropriate for the current stage.
        
        Args:
            stage: The current execution stage
            state: Current runtime state view
            
        Returns:
            Assembled context ready for the model
        """
        ...

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget",
    ) -> RetrievedContext:
        """Retrieve relevant context for a query.
        
        Args:
            query: The search query
            budget: Budget constraints for retrieval
            
        Returns:
            Retrieved context items
        """
        ...

    async def ensure_index(self, scope: str) -> IndexStatus:
        """Ensure the index for a scope is ready.
        
        Args:
            scope: The scope to index
            
        Returns:
            Index status information
        """
        ...

    async def compress(
        self,
        context: AssembledContext,
        *,
        budget: "Budget",
    ) -> AssembledContext:
        """Compress context to fit within budget.
        
        Args:
            context: The context to compress
            budget: Budget constraints
            
        Returns:
            Compressed context
        """
        ...

    async def route(self, packet: ContextPacket, target: str) -> None:
        """Route a context packet to another agent/session.
        
        Args:
            packet: The context packet to route
            target: Target identifier
        """
        ...
