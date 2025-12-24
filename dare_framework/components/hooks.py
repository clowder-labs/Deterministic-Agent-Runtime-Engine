from __future__ import annotations

from ..core.interfaces import IHook
from ..core.models import Event


class NoOpHook(IHook):
    async def on_event(self, event: Event) -> None:
        return None
