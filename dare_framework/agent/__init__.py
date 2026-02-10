"""agent domain facade."""

from dare_framework.agent.interfaces import IAgentOrchestration
from dare_framework.agent.kernel import IAgent
from dare_framework.agent.status import AgentStatus
from dare_framework.agent.types import AgentDeps, ISessionSummaryStore
from dare_framework.agent.base_agent import BaseAgent
from dare_framework.agent.dare_agent import DareAgent
from dare_framework.agent.react_agent import ReactAgent
from dare_framework.agent.simple_chat import SimpleChatAgent
from dare_framework.agent.builder import (
    DareAgentBuilder,
    ReactAgentBuilder,
    SimpleChatAgentBuilder,
)

__all__ = [
    "AgentDeps",
    "ISessionSummaryStore",
    "IAgent",
    "AgentStatus",
    "IAgentOrchestration",
    "BaseAgent",
    "DareAgent",
    "ReactAgent",
    "SimpleChatAgent",
    "DareAgentBuilder",
    "ReactAgentBuilder",
    "SimpleChatAgentBuilder",
]
