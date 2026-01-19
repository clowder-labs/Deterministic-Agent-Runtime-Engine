"""Builder domain: Agent composition and plugin system.

This domain provides the developer-facing API for building
Agent instances with pluggable components.
"""

from dare_framework2.builder.agent import Agent
from dare_framework2.builder.builder import AgentBuilder
from dare_framework2.builder.types import (
    ComponentType,
    PluginManagers,
    BaseComponent,
    # Manager interfaces
    IToolManager,
    IModelAdapterManager,
    IPlannerManager,
    IValidatorManager,
    IRemediatorManager,
    IProtocolAdapterManager,
    IHookManager,
    IConfigProviderManager,
    IMemoryManager,
    IPromptStoreManager,
    ISkillManager,
)
from dare_framework2.builder.plugin import (
    NoOpToolManager,
    NoOpModelAdapterManager,
    NoOpPlannerManager,
    NoOpValidatorManager,
    NoOpRemediatorManager,
    NoOpProtocolAdapterManager,
    NoOpHookManager,
    NoOpConfigProviderManager,
    NoOpMemoryManager,
    NoOpPromptStoreManager,
    NoOpSkillManager,
)

__all__ = [
    # Core classes
    "Agent",
    "AgentBuilder",
    # Types
    "ComponentType",
    "PluginManagers",
    "BaseComponent",
    # Manager interfaces
    "IToolManager",
    "IModelAdapterManager",
    "IPlannerManager",
    "IValidatorManager",
    "IRemediatorManager",
    "IProtocolAdapterManager",
    "IHookManager",
    "IConfigProviderManager",
    "IMemoryManager",
    "IPromptStoreManager",
    "ISkillManager",
    # No-op implementations
    "NoOpToolManager",
    "NoOpModelAdapterManager",
    "NoOpPlannerManager",
    "NoOpValidatorManager",
    "NoOpRemediatorManager",
    "NoOpProtocolAdapterManager",
    "NoOpHookManager",
    "NoOpConfigProviderManager",
    "NoOpMemoryManager",
    "NoOpPromptStoreManager",
    "NoOpSkillManager",
]
