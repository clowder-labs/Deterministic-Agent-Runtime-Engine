"""transport domain stable interfaces (kernel boundaries)."""

from __future__ import annotations

from typing import Any, Awaitable, Protocol

from dare_framework.transport.types import (
    EnvelopeDecoder,
    EnvelopeEncoder,
    Receiver,
    Sender,
    TransportEnvelope,
)


class ClientChannel(Protocol):
    """Client-facing adapter contract for transport."""

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        """Attach the sender used to push envelopes into the agent inbox."""

    def agent_envelope_receiver(self) -> Receiver:
        """Return the receiver used to deliver envelopes from the agent outbox."""


class AgentChannel(Protocol):
    """Agent-facing channel contract for transport."""

    async def start(self) -> None:
        """Start the channel pump (idempotent)."""

    async def stop(self) -> None:
        """Stop the channel pump and drop pending outgoing messages."""

    async def poll(self) -> TransportEnvelope:
        """Poll the next incoming envelope from the client."""

    async def send(self, msg: TransportEnvelope) -> None:
        """Send an outgoing envelope to the client (may apply backpressure)."""

    async def run_interruptible(self, coro: Awaitable[Any]) -> Any:
        """Run a coroutine that can be interrupted via interrupt()."""

    def interrupt(self) -> None:
        """Interrupt the current run_interruptible task if active."""

    @staticmethod
    def build(
        client_channel: ClientChannel,
        *,
        max_inbox: int = 100,
        max_outbox: int = 100,
        encoder: EnvelopeEncoder | None = None,
        decoder: EnvelopeDecoder | None = None,
    ) -> AgentChannel:
        """Create the default AgentChannel implementation.

        Optional encoder/decoder allow envelope transforms at the agent boundary.
        """

        from dare_framework.transport._internal.default_channel import DefaultAgentChannel

        return DefaultAgentChannel(
            client_channel,
            max_inbox=max_inbox,
            max_outbox=max_outbox,
            encoder=encoder,
            decoder=decoder,
        )


__all__ = ["AgentChannel", "ClientChannel"]
