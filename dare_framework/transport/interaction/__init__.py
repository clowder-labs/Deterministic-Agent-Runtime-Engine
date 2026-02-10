"""Interaction dispatch helpers for transport-driven sessions.

This module lives under the transport domain (but outside the transport kernel boundary)
to keep AgentChannel content-agnostic while providing a default way to route:
- prompt messages (LLM execution)
- deterministic actions (resource:action)
- runtime controls (AgentControl)
"""

from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.controls import AgentControl
from dare_framework.transport.interaction.dispatcher import ActionHandlerDispatcher

__all__ = ["AgentControl", "ActionHandlerDispatcher", "ResourceAction"]
