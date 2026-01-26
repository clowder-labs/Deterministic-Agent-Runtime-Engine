"""Event domain: audit logging and event listening.

This domain handles event logging for audit trails, replay functionality,
and real-time event listening.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.event.component import IEventLog, IEventListener

# Common types (users may construct or use for type annotations)
from dare_framework3_2.event.types import Event

# Default implementations
from dare_framework3_2.event.impl.local_event_log import LocalEventLog
from dare_framework3_2.event.impl.noop_listener import NoopListener

__all__ = [
    # Protocol
    "IEventLog",
    "IEventListener",
    # Types
    "Event",
    # Implementations
    "LocalEventLog",
    "NoopListener",
]
