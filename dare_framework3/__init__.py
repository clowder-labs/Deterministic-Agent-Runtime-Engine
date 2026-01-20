"""DARE Framework v3 (v3.2 architecture)."""

from dare_framework3.agent import BaseAgent, FiveLayerAgent, SimpleChatAgent
from dare_framework3.plan.types import Task, Milestone, RunResult

__all__ = [
    "BaseAgent",
    "FiveLayerAgent",
    "SimpleChatAgent",
    "Task",
    "Milestone",
    "RunResult",
]

__version__ = "3.2.0"
