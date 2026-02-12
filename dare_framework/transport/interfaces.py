"""transport domain pluggable interfaces."""

from __future__ import annotations

from dare_framework.transport.kernel import AgentChannel, ClientChannel, PollableClientChannel

__all__ = ["AgentChannel", "ClientChannel", "PollableClientChannel"]
