"""event domain facade."""

from dare_framework.event._internal.sqlite_event_log import DefaultEventLog, SQLiteEventLog
from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event, RuntimeSnapshot

__all__ = [
    "Event",
    "IEventLog",
    "RuntimeSnapshot",
    "SQLiteEventLog",
    "DefaultEventLog",
]
