"""Context domain component interfaces (Protocol definitions)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from dare_framework3_2.context.types import (
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
    from dare_framework3_2.plan.types import Task


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
        budget: Budget,
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
        budget: Budget,
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


class IContextStrategy(Protocol):
    """Strategy for building prompts from assembled context.
    
    Allows customization of how context is transformed into
    the final prompt sent to the model.
    """

    async def build_prompt(self, assembled: AssembledContext) -> Prompt:
        """Build a prompt from assembled context.
        
        Args:
            assembled: The assembled context
            
        Returns:
            The final prompt for the model
        """
        ...


# =============================================================================
# Resource Manager Interface (migrated from runtime/)
# =============================================================================

class IResourceManager(Protocol):
    """Unified budget model and accounting.
    
    Tracks resource consumption against budgets and raises
    ResourceExhausted when limits are exceeded.
    
    Migrated from runtime/ in v3.2 as it primarily manages context resources.
    """

    def get_budget(self, scope: str) -> Budget:
        """Get the budget for a scope.
        
        Args:
            scope: Budget scope identifier
            
        Returns:
            Budget for the scope
        """
        ...

    def acquire(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        """Reserve resources for a scope.
        
        Args:
            resource: Type of resource
            amount: Amount to acquire
            scope: Budget scope
            
        Raises:
            ResourceExhausted: If budget would be exceeded
        """
        ...

    def record(
        self,
        resource: ResourceType,
        amount: float,
        *,
        scope: str,
    ) -> None:
        """Record consumption for audit and feedback loops.
        
        Args:
            resource: Type of resource
            amount: Amount consumed
            scope: Budget scope
        """
        ...

    def check_limit(self, *, scope: str) -> None:
        """Check if scope is within budget.
        
        Args:
            scope: Budget scope
            
        Raises:
            ResourceExhausted: If scope is over budget
        """
        ...
