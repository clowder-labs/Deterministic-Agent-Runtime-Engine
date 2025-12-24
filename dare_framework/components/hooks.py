from __future__ import annotations

from ..core.interfaces import IHook
from ..core.models import Event
from .base_component import BaseComponent


class NoOpHook(BaseComponent, IHook):
    async def on_event(self, event: Event) -> None:
        return None
