"""agent domain facade."""

from dare_framework.agent.interfaces import IAgentOrchestration
from dare_framework.agent.kernel import IAgent
from dare_framework.agent.types import AgentDeps
from dare_framework.agent.base_agent import BaseAgent
from dare_framework.agent._internal.five_layer import DareAgent
from dare_framework.agent._internal.react_agent import ReactAgent
from dare_framework.agent._internal.simple_chat import SimpleChatAgent
from dare_framework.agent._internal.builder import (
    DareAgentBuilder,
    ReactAgentBuilder,
    SimpleChatAgentBuilder,
)

__all__ = [
    "AgentDeps",
    "IAgent",
    "IAgentOrchestration",
    "BaseAgent",
    "DareAgent",
    "ReactAgent",
    "SimpleChatAgent",
    "DareAgentBuilder",
    "ReactAgentBuilder",
    "SimpleChatAgentBuilder",
]

