"""Internal event implementations."""

from dare_framework.event._internal.sqlite_event_log import DefaultEventLog, SQLiteEventLog

__all__ = ["SQLiteEventLog", "DefaultEventLog"]
