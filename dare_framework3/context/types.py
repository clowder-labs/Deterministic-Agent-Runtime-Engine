"""Context domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dare_framework3.model.types import Message


class ContextStage(Enum):
    """Context assembly stages aligned to the five-layer loop.
    
    Each stage corresponds to a different phase in the agent's
    execution cycle, requiring different context composition.
    """
    SESSION_OBSERVE = "session_observe"
    MILESTONE_OBSERVE = "milestone_observe"
    PLAN = "plan"
    EXECUTE = "execute"
    TOOL = "tool"
    VERIFY = "verify"


@dataclass(frozen=True)
class AssembledContext:
    """The assembled context window input with attribution metadata.
    
    Represents the fully assembled prompt that will be sent to the LLM,
    along with metadata about what was included and why.
    
    Attributes:
        messages: The conversation messages for the LLM
        metadata: Attribution and debugging information
    """
    messages: list["Message"]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Prompt:
    """A final prompt representation for model adapters.
    
    Attributes:
        messages: The conversation messages
        metadata: Additional prompt metadata
    """
    messages: list["Message"]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedContext:
    """Retrieval output for context assembly.
    
    Contains items retrieved from memory or other sources
    to be included in the context.
    
    Attributes:
        items: List of retrieved items as dictionaries
    """
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class IndexStatus:
    """Index readiness status for a scope.
    
    Indicates whether the index for a given scope is ready
    for retrieval operations.
    
    Attributes:
        ready: Whether the index is ready
        details: Additional status information
    """
    ready: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextPacket:
    """Cross-window / cross-agent context handoff packet.
    
    Used for routing context between agents or sessions.
    
    Attributes:
        id: Unique packet identifier
        source: Source agent/session identifier
        target: Target agent/session identifier
        summary: Compressed summary of the context
        attachments: References to attached artifacts
        budget_attribution: Token/cost attribution data
    """
    id: str
    source: str
    target: str
    summary: str
    attachments: list[str] = field(default_factory=list)
    budget_attribution: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeStateView:
    """Minimal state view for context assembly.
    
    Provides the context manager with the current runtime state
    needed to assemble appropriate prompts.
    
    Attributes:
        task_id: Current task identifier
        run_id: Current run identifier
        milestone_id: Current milestone identifier (if any)
        stage: Current context stage
        data: Additional state data
    """
    task_id: str
    run_id: str
    milestone_id: str | None
    stage: ContextStage
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """A session-scoped context holder.
    
    Returned by IContextManager.open_session() to track
    session-level context state.
    
    Attributes:
        user_input: The initial user input
        metadata: Session metadata (e.g., task_id)
    """
    user_input: str
    metadata: dict[str, Any] = field(default_factory=dict)
