"""Kernel event domain (v2)."""

from .protocols import IEventLog
from .local_event_log import LocalEventLog
from .models import Event

__all__ = ["IEventLog", "LocalEventLog", "Event"]
