"""agent domain facade."""

from dare_framework3_4.agent.interfaces import IAgentOrchestration
from dare_framework3_4.agent.kernel import IAgent
from dare_framework3_4.agent.types import AgentDeps
from dare_framework3_4.agent._internal.base import BaseAgent
from dare_framework3_4.agent._internal.simple_chat import SimpleChatAgent

__all__ = [
    "AgentDeps",
    "IAgent",
    "IAgentOrchestration",
    "BaseAgent",
    "SimpleChatAgent",
]
