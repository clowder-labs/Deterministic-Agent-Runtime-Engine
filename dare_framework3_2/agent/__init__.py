"""Agent module - User-facing API for DARE Framework.

This module provides the primary user interface for creating and running agents.
Users interact with Agent subclasses rather than dealing with Kernel internals directly.

Classes:
    BaseAgent: Abstract base class for all agent implementations
    FiveLayerAgent: Five-layer loop agent (Session -> Milestone -> Plan -> Execute -> Tool)
    SimpleChatAgent: Simple chat agent [placeholder]
"""

from dare_framework3_2.agent.base import BaseAgent
from dare_framework3_2.agent.five_layer import FiveLayerAgent
from dare_framework3_2.agent.simple_chat import SimpleChatAgent

__all__ = [
    "BaseAgent",
    "FiveLayerAgent",
    "SimpleChatAgent",
]
