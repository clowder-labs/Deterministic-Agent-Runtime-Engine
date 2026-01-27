#/events/base.py
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from framework.agents.agent_execution_context import AgentExecutionContext
    from framework.core import Message
    from framework.models.base import ModelResponse
    from framework.workflow.core import WorkflowExecutionContext


class EventType(str, Enum):
    """Event type categorization."""

    AGENT = "agent"
    TOOL = "tool"
    NODE = "node"
    WORKFLOW = "workflow"
    LLM = "llm"
    LLM_CHUNK = "llm_chunk"


class EventPhase(str, Enum):
    """Event phase in execution lifecycle."""

    BEFORE = "before"
    AFTER = "after"


class Priority(int, Enum):
    """Listener priority levels.
    Use the priorities below for listener order execution.
    Lower numbers will execute first.
    SECURITY_* priorities should not be used for any business logic and are reserved for Security listeners.
    """

    SECURITY_FIRST = 0
    CRITICAL = 10
    HIGH = 50
    NORMAL = 100
    LOW = 200
    SECURITY_LAST = 300


class EventMode(str, Enum):
    INTERCEPTOR = "interceptor"
    OBSERVER = "observer"


@dataclass
class Event:
    """
    Base event class.

    Attributes:
        context: Full execution context with all agent state
        phase: Whether this is a BEFORE or AFTER event
        event_type: Type of event (AGENT or TOOL or Custom)
        id: Unique event identifier
        timestamp: When the event was created
    """

    event_type: EventType | str
    phase: EventPhase
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self):
        fields = []
        for field_name, value in self.__dict__.items():
            if value is not None and value != "":
                fields.append(f"{field_name}={value}")
        return f"{self.__class__.__name__}({', '.join(fields)})"


@dataclass(kw_only=True)
class AgentEvent(Event):
    """
    Represents an agent-related event in the system.

    It is triggered during agent execution lifecycle and contains the execution context
    Events are MUTABLE - listeners can modify them to change behavior through `Interceptor`s

    Attributes:
        context: The execution context containing agent state and data
    """

    context: AgentExecutionContext


@dataclass(kw_only=True)
class WorkflowEvent(Event):
    """
    Represents a workflow-related event in the system.

    It is triggered during workflow execution lifecycle and contains the execution context
    Events are MUTABLE - listeners can modify them to change behavior through `Interceptor`s

    Attributes:
        context: The execution context containing agent state and data
    """

    context: WorkflowExecutionContext


@dataclass(kw_only=True)
class LLMEvent(Event):
    """
    Represents an LLM-related event in the system.

    It is triggered during LLM execution lifecycle and contains information about
    the LLM call, including model details, input/output, and timing information.
    Events are MUTABLE - listeners can modify them to change behavior through `Interceptor`s

    Attributes:
        model: The LLM model being used
        input: The input prompt or messages sent to the LLM
        output: The output response from the LLM (for AFTER events)
    """

    model_name: str
    input: list[Message]
    output: ModelResponse | None = None


class EventBusProtocol(Protocol):
    def add_observer(
        self,
        handler: Callable[[Event], Awaitable[None]],
        event_type: EventType | str = "*",
        event_phase: EventPhase | str = "*",
    ) -> None:
        """
        Subscribe to events as an observer. Observers should not modify context or affect the flow. They are run concurrently.
        They are triggered after all interceptors for the event have run.

        Observers are meant for observation purposes only - logging, metrics collection, etc. They should not modify
        the event context or influence the execution flow.

        Args:
            handler: Async function to call when event matches
            event_type: The Event Type to subscribe to (e.g. EventType.TOOL, EventType.AGENT, or "*" for all)
            event_phase: EventPhase.BEFORE, EventPhase.AFTER, or "*" for all

        Examples:
            bus.add_observer(my_handler, EventType.TOOL, EventPhase.AFTER)
            bus.add_observer(my_handler, EventType.AGENT, "*")  # All agent events
            bus.add_observer(my_handler, "*", EventPhase.BEFORE)  # All before events
            bus.add_observer(my_handler)  # All events (defaults to "*", "*")
        """
        ...

    def add_interceptor(
        self,
        handler: Callable[[Event], Awaitable[None]],
        event_type: EventType | str = "*",
        event_phase: EventPhase | str = "*",
        priority: Priority | int = Priority.NORMAL,
    ) -> None:
        """
        Subscribe to events as interceptor. Interceptors can modify the flow and execution context and are run sequentially by priority.

        Interceptors are allowed to modify the event context, cancel execution, or complete the flow. They run in priority order
        (lower numbers execute first) and can influence the execution path. They are run before observers for the same event.

        Args:
            handler: Async function to call when event matches
            event_type: The Event Type to subscribe to (e.g. EventType.TOOL, EventType.AGENT, or "*" for all)
            event_phase: EventPhase.BEFORE, EventPhase.AFTER, or "*" for all
            priority: Priority enum or int (lower = earlier execution)

        Examples:
            bus.add_interceptor(my_handler, EventType.TOOL, EventPhase.AFTER)
            bus.add_interceptor(my_handler, EventType.AGENT, "*")  # All agent events
            bus.add_interceptor(my_handler, "*", EventPhase.BEFORE)  # All before events
            bus.add_interceptor(my_handler)  # All events (defaults to "*", "*")
        """
        ...

    def clear(self) -> None:
        """
        Clear all event listeners. Useful for testing or resetting the event bus state.
        """
        ...

    async def emit(self, event: Event) -> None:
        """
        Emit an event to all matching listeners.
        """
        ...

    @classmethod
    def get_instance(cls) -> EventBusProtocol:
        """
        Get the singleton instance of the EventBus.
        """
        ...
