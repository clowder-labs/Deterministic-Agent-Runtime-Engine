"""DARE Framework v3.2 - Deterministic Agent Runtime Engine.

A industrial-grade AI Agent execution framework with a kernelized architecture,
providing deterministic, auditable, and extensible agent execution.

v3.2 Architecture:
- agent/: User API layer (BaseAgent, FiveLayerAgent, SimpleChatAgent)
- context/: Context engineering and resource management
- model/: LLM adapter interfaces
- memory/: Persistent storage and retrieval
- tool/: Tool execution and execution control
- plan/: Planning, validation, remediation
- event/: Audit logging and event listening (new in v3.2)
- hook/: Extension points and hook callbacks (new in v3.2)
- security/: Trust, policy, and sandbox boundary
- config/: Configuration management
- utils/: Common utilities

Key Changes from v3.1:
- runtime/ deleted, responsibilities distributed to:
  - IResourceManager -> context/
  - IExecutionControl -> tool/
  - IEventLog -> event/ (new domain)
  - IExtensionPoint, IHook -> hook/ (new domain)
- interfaces.py renamed to component.py
- Empty kernel.py added to each domain for future stable interfaces
- Factory functions removed, __init__.py directly exports implementation classes

Usage:
    from dare_framework3_2 import FiveLayerAgent, Task
    
    agent = FiveLayerAgent(name="my_agent", model=model, tools=[tool1, tool2])
    result = await agent.run("Complete this task")
"""

from dare_framework3_2.agent import BaseAgent, FiveLayerAgent, SimpleChatAgent
from dare_framework3_2.plan.types import Task, Milestone, RunResult

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

__version__ = "3.2.0"
