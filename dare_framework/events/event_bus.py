#/events/eventbus.py
"""Event bus for managing event subscriptions and publishing."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import NamedTuple

from framework.events.base import (
    Event,
    EventBusProtocol,
    EventMode,
    EventPhase,
    EventType,
    Priority,
)
from framework.utils.logging import get_logger
from framework.utils.type_helpers import resolve_int, resolve_str

# Get logger for this module
logger = get_logger(__name__)


class _EventListener(NamedTuple):
    priority: int
    mode: EventMode
    handler: Callable[[Event], Awaitable[None]]


class EventBus(EventBusProtocol):
    """
    Unified event bus for observability AND interception.

    - listeners can observe events (logging, metrics)
    - listeners can modify events (change data, add context)
    - listeners can cancel events (validation, safety checks)
    - Priority system ensures correct execution order
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance."""
        cls._instance = None

    def __init__(self):
        self.listeners: dict[str, list[_EventListener]] = {}
        self._observer_tasks: set[asyncio.Task] = set()

    def add_observer(
        self,
        handler: Callable[[Event], Awaitable[None]],
        event_type: EventType | str = "*",
        event_phase: EventPhase | str = "*",
    ) -> None:
        """
        Subscribe to events as observer. Observers should not modify context or affect the flow. They are run concurrently.
        They are triggered after all interceptors for the event have run.

        Observers are meant for observation purposes only - logging, metrics collection, etc. They should not modify
        the event context or influence the execution flow. They run in parallel with other observers for the same event.

        Args:
            handler: Async function to call when event matches
            event_type: EventType.TOOL, EventType.AGENT, or "*" for all
            event_phase: EventPhase.BEFORE, EventPhase.AFTER, or "*" for all

        Examples:
            bus.add_observer(my_handler, EventType.TOOL, EventPhase.AFTER)
            bus.add_observer(my_handler, EventType.AGENT, "*")  # All agent events
            bus.add_observer(my_handler, "*", EventPhase.BEFORE)  # All before events
            bus.add_observer(my_handler)  # All events (defaults to "*", "*")
        """
        self._register_listener(
            event_mode=EventMode.OBSERVER,
            handler=handler,
            event_type=event_type,
            event_phase=event_phase,
        )

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
            event_type: EventType.TOOL, EventType.AGENT, or "*" for all
            event_phase: EventPhase.BEFORE, EventPhase.AFTER, or "*" for all
            priority: Priority enum or int (lower = earlier execution)

        Examples:
            bus.add_interceptor(my_handler, EventType.TOOL, EventPhase.AFTER)
            bus.add_interceptor(my_handler, EventType.AGENT, "*")  # All agent events
            bus.add_interceptor(my_handler, "*", EventPhase.BEFORE)  # All before events
            bus.add_interceptor(my_handler)  # All events (defaults to "*", "*")
        """
        self._register_listener(
            event_mode=EventMode.INTERCEPTOR,
            handler=handler,
            event_type=event_type,
            event_phase=event_phase,
            priority=priority,
        )

    def _register_listener(
        self,
        handler: Callable[[Event], Awaitable[None]],
        event_mode: EventMode,
        event_type: EventType | str = "*",
        event_phase: EventPhase | str = "*",
        priority: Priority | int = Priority.NORMAL,
    ) -> None:
        # Convert enums to values
        type_str = resolve_str(event_type)
        phase_str = resolve_str(event_phase)
        priority_int = resolve_int(priority)

        valid_phases = {phase.value for phase in EventPhase} | {"*"}

        if phase_str not in valid_phases:
            # Fallback for manual strings if needed, or raise error
            valid_list = ", ".join(sorted(valid_phases))
            raise ValueError(
                f"Invalid event_phase '{event_phase}'. Must be one of: {valid_list}"
            )

        # Build key for storage
        key = f"{type_str}:{phase_str}"

        if key not in self.listeners:
            self.listeners[key] = []

        self.listeners[key].append(
            _EventListener(priority=priority_int, mode=event_mode, handler=handler)
        )
        # Sort by priority
        self.listeners[key].sort(key=lambda x: x.priority)

        logger.debug(
            f"Subscribed handler to event: type={type_str}, phase={phase_str}, priority={priority_int}, mode={event_mode}"
        )

    def clear(self) -> None:
        """Clear all event listeners. Useful for testing."""
        self.listeners.clear()

    async def emit(self, event: Event) -> None:
        """
        Emit event to all matching listeners.
        listeners execute in priority order and can modify the event.
        """
        # Build keys to check (in order of specificity)
        event_type = resolve_str(event.event_type)
        event_phase = resolve_str(event.phase)

        keys_to_check = [
            f"{event_type}:{event_phase}",  # Exact match: "tool:after"
            f"{event_type}:*",  # Type wildcard: "tool:*"
            f"*:{event_phase}",  # Phase wildcard: "*:after"
            "*:*",  # All events
        ]

        # Collect all matching listeners with priorities
        matching_listeners: list[_EventListener] = []
        for key in keys_to_check:
            if key in self.listeners:
                matching_listeners.extend(self.listeners[key])

        # Sort by priority and remove duplicates while preserving order
        seen = set()
        unique_listeners: list[_EventListener] = []
        for listener in sorted(matching_listeners, key=lambda x: x.priority):
            handler_id = id(listener.handler)
            if handler_id not in seen:
                seen.add(handler_id)
                unique_listeners.append(listener)

        interceptors = []
        observers = []
        for listener in unique_listeners:
            if listener.mode == EventMode.INTERCEPTOR:
                interceptors.append(listener)
            elif listener.mode == EventMode.OBSERVER:
                observers.append(listener)

        logger.debug(
            f"Emitting event: type={event_type}, phase={event_phase}, event_id={getattr(event, 'id', 'unknown')} {event}"
        )

        # Execute interceptors in order
        for interceptor in interceptors:
            try:
                await interceptor.handler(event)

            except Exception as e:
                logger.error(
                    f"Error in event handler for event {event_type}:{event_phase}: {e}"
                )

        for observer in observers:
            task = asyncio.create_task(self._run_observer(observer.handler, event))

            self._observer_tasks.add(task)
            task.add_done_callback(self._observer_tasks.discard)

    async def wait_for_observers(self, timeout: float | None = None) -> None:
        """
        Wait for all observer tasks to complete.

        Useful during graceful shutdown / testing.

        Args:
            timeout: Max time to wait in seconds (None = wait forever)
        """
        if not self._observer_tasks:
            return

        task_count = len(self._observer_tasks)
        logger.info(f"Waiting for {task_count} observer tasks to complete...")

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._observer_tasks, return_exceptions=True),
                timeout=timeout,
            )
            logger.info(f"All {task_count} observers completed")
        except asyncio.TimeoutError:
            remaining = len(self._observer_tasks)
            logger.warning(
                f"{remaining} of {task_count} observers did not complete "
                f"within {timeout}s timeout"
            )

    async def _run_observer(self, handler: Callable, event: Event) -> None:
        try:
            await handler(event)
        except Exception:
            handler_name = getattr(handler, "__name__", repr(handler))
            logger.exception(f"Error in observer {handler_name}")
            
