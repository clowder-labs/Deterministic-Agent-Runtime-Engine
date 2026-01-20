"""DARE Framework v3 (v3.3 architecture)."""

from dare_framework3_3.agent import BaseAgent, FiveLayerAgent, SimpleChatAgent
from dare_framework3_3.plan.types import Task, Milestone, RunResult

__all__ = [
    "BaseAgent",
    "FiveLayerAgent",
    "SimpleChatAgent",
    "Task",
    "Milestone",
    "RunResult",
]

__version__ = "3.3.0"
