"""Default transport channel implementation."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Awaitable

from dare_framework.transport.kernel import AgentChannel, ClientChannel
from dare_framework.transport.types import (
    EnvelopeDecoder,
    EnvelopeEncoder,
    Receiver,
    Sender,
    TransportEnvelope,
)

_logger = logging.getLogger("dare.transport")


class DefaultAgentChannel(AgentChannel):
    """Queue-based AgentChannel with blocking backpressure and pump delivery."""

    def __init__(
        self,
        client_channel: ClientChannel,
        *,
        max_inbox: int,
        max_outbox: int,
        encoder: EnvelopeEncoder | None = None,
        decoder: EnvelopeDecoder | None = None,
    ) -> None:
        self._client = client_channel
        self._receiver: Receiver = client_channel.agent_envelope_receiver()
        self._encoder = encoder or _identity_envelope
        self._decoder = decoder or _identity_envelope

        self._inbox: asyncio.Queue[TransportEnvelope] = asyncio.Queue(maxsize=max_inbox)
        self._outbox: asyncio.Queue[TransportEnvelope] = asyncio.Queue(maxsize=max_outbox)

        self._current_task: asyncio.Task[Any] | None = None
        self._started = False
        self._out_pump_task: asyncio.Task[None] | None = None

        async def sender(msg: TransportEnvelope) -> None:
            try:
                await self._enqueue_inbox(msg)
            except Exception:
                _logger.exception("agent channel sender failed")

        client_channel.attach_agent_envelope_sender(sender)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._out_pump_task = asyncio.create_task(self._pump_outbox_to_receiver())

    async def stop(self) -> None:
        if self._out_pump_task is not None:
            self._out_pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._out_pump_task
        self._out_pump_task = None
        self._started = False
        self._drain_outbox()

    async def poll(self) -> TransportEnvelope:
        return await self._inbox.get()

    async def send(self, msg: TransportEnvelope) -> None:
        try:
            encoded = self._encoder(msg)
        except Exception:
            _logger.exception("agent channel encoder failed")
            return
        await self._outbox.put(encoded)

    async def run_interruptible(self, coro: Awaitable[Any]) -> Any:
        self._current_task = asyncio.create_task(coro)
        try:
            return await self._current_task
        finally:
            self._current_task = None

    def interrupt(self) -> None:
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    async def _pump_outbox_to_receiver(self) -> None:
        while True:
            msg = await self._outbox.get()
            try:
                await self._receiver(msg)
            except Exception:
                _logger.exception("agent channel receiver failed")

    async def _enqueue_inbox(self, msg: TransportEnvelope) -> None:
        try:
            decoded = self._decoder(msg)
        except Exception:
            _logger.exception("agent channel decoder failed")
            return
        await self._inbox.put(decoded)

    def _drain_outbox(self) -> None:
        while not self._outbox.empty():
            with contextlib.suppress(asyncio.QueueEmpty):
                self._outbox.get_nowait()


def _identity_envelope(envelope: TransportEnvelope) -> TransportEnvelope:
    return envelope
