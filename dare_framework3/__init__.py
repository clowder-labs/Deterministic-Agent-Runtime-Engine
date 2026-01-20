"""DARE Framework v3 - Deterministic Agent Runtime Engine.

A industrial-grade AI Agent execution framework with a kernelized architecture,
providing deterministic, auditable, and extensible agent execution.

v3 Architecture (v3.1):
- Layer 0 (Kernel): Core runtime infrastructure (runtime/, security/, context/, tool/)
- Layer 1 (Protocol Adapters): External protocol integration (MCP, A2A, etc.)
- Layer 2 (Components): Pluggable strategy implementations (plan/, memory/, model/)
- Layer 3 (Developer API): Agent classes (agent/)

Key Changes from v2:
- AgentBuilder replaced by Agent class hierarchy (BaseAgent, FiveLayerAgent, etc.)
- execution/ renamed to runtime/
- IRunLoop, ILoopOrchestrator removed (execution logic moved to Agent classes)
- ISecurityBoundary moved to security/ domain
- Factory functions added to each domain for DIP compliance

Usage:
    from dare_framework3 import FiveLayerAgent, Task
    
    agent = FiveLayerAgent(name="my_agent", model=model, tools=[tool1, tool2])
    result = await agent.run("Complete this task")
"""

from dare_framework3.agent import BaseAgent, FiveLayerAgent, SimpleChatAgent
from dare_framework3.plan.types import Task, Milestone, RunResult

__all__ = [
    # Primary API - Agent classes
    "BaseAgent",
    "FiveLayerAgent",
    "SimpleChatAgent",
    # Task types
    "Task",
    "Milestone",
    "RunResult",
]

__version__ = "3.0.0"
