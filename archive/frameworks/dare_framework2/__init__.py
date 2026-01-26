"""DARE Framework v2 - Deterministic Agent Runtime Engine.

A industrial-grade AI Agent execution framework with a kernelized architecture,
providing deterministic, auditable, and extensible agent execution.

Architecture Overview:
- Layer 0 (Kernel): Immutable infrastructure with five-layer loop orchestration
- Layer 1 (Protocol Adapters): External protocol integration (MCP, A2A, etc.)
- Layer 2 (Components): Pluggable strategy implementations
- Layer 3 (Developer API): AgentBuilder and high-level interfaces

Usage:
    from dare_framework2 import Agent, AgentBuilder, Task
    
    agent = AgentBuilder.quick_start("my_agent").build()
    result = await agent.run("Hello, world!")
"""

from dare_framework2.builder import Agent, AgentBuilder
from dare_framework2.plan.types import Task, Milestone, RunResult

__all__ = [
    # Primary API
    "Agent",
    "AgentBuilder",
    "Task",
    "Milestone",
    "RunResult",
]

__version__ = "2.0.0"
