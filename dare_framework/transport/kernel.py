"""transport domain stable interfaces (kernel boundaries)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from dare_framework.transport.types import (
    Receiver,
    Sender,
    TransportEnvelope,
)

if TYPE_CHECKING:
    from dare_framework.transport.interaction.control_handler import AgentControlHandler
    from dare_framework.transport.interaction.dispatcher import ActionHandlerDispatcher


class ClientChannel(Protocol):
    """Client-facing adapter contract for transport."""

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        """Attach the sender used to push envelopes into the agent inbox."""

    def agent_envelope_receiver(self) -> Receiver:
        """Return the receiver used to deliver envelopes from the agent outbox."""


@runtime_checkable
class PollableClientChannel(ClientChannel, Protocol):
    """Extension for client channels that support polling unsolicited events."""

    async def poll(self, timeout: float | None = None) -> TransportEnvelope | None:
        """Poll unsolicited envelopes emitted by the agent channel."""


class AgentChannel(Protocol):
    """Agent-facing channel contract for transport."""

    async def start(self) -> None:
        """Start the channel pump (idempotent)."""

    async def stop(self) -> None:
        """Stop the channel pump and drop pending outgoing messages."""

    async def poll(self) -> TransportEnvelope | list[TransportEnvelope]:
        """Poll the next incoming envelope(s) from the client."""

    async def send(self, msg: TransportEnvelope) -> None:
        """Send an outgoing envelope to the client (may apply backpressure)."""

    def add_action_handler_dispatcher(self, dispatcher: ActionHandlerDispatcher) -> None:
        """Attach action dispatcher configured by agent builder/runtime."""

    def add_agent_control_handler(self, handler: AgentControlHandler) -> None:
        """Attach control handler configured by agent builder/runtime."""

    def get_action_handler_dispatcher(self) -> ActionHandlerDispatcher | None:
        """Return attached action dispatcher if configured."""

    def get_agent_control_handler(self) -> AgentControlHandler | None:
        """Return attached control handler if configured."""

    @staticmethod
    def build(
        client_channel: ClientChannel,
        *,
        max_inbox: int = 100,
        max_outbox: int = 100,
        action_timeout_seconds: float = 30.0,
    ) -> AgentChannel:
        """Create the default AgentChannel implementation.

        `action_timeout_seconds` controls the timeout guard for ACTION dispatches.
        """

        from dare_framework.transport._internal.default_channel import DefaultAgentChannel

        return DefaultAgentChannel(
            client_channel,
            max_inbox=max_inbox,
            max_outbox=max_outbox,
            action_timeout_seconds=action_timeout_seconds,
        )


__all__ = ["AgentChannel", "ClientChannel", "PollableClientChannel"]
