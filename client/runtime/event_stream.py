"""Consume unsolicited transport messages from DirectClientChannel."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from dare_framework.transport import DirectClientChannel
from dare_framework.transport.serialization import jsonify_transport_value

EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


async def drain_events(
    client_channel: DirectClientChannel,
    *,
    on_event: EventHandler,
    max_items: int = 20,
) -> int:
    """Drain currently available unsolicited envelopes without blocking."""
    count = 0
    for _ in range(max_items):
        envelope = await client_channel.poll(timeout=0.0)
        if envelope is None:
            break
        payload = jsonify_transport_value(envelope.payload)
        if isinstance(payload, dict):
            maybe_awaitable = on_event(payload)
            if maybe_awaitable is not None:
                await maybe_awaitable
        count += 1
    return count


@dataclass
class EventPump:
    """Background poller for unsolicited transport events."""

    client_channel: DirectClientChannel
    on_event: EventHandler
    interval_seconds: float = 0.2
    _task: asyncio.Task[None] | None = None
    _running: bool = False

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while self._running:
            try:
                envelope = await self.client_channel.poll(timeout=self.interval_seconds)
            except Exception:
                await asyncio.sleep(self.interval_seconds)
                continue
            if envelope is None:
                continue
            payload = jsonify_transport_value(envelope.payload)
            if not isinstance(payload, dict):
                continue
            maybe_awaitable = self.on_event(payload)
            if maybe_awaitable is not None:
                await maybe_awaitable
