"""Utility functions and common types."""

from dare_framework3.utils.ids import generate_id
from dare_framework3.utils.errors import (
    ToolError,
    ToolNotFoundError,
    ToolAccessDenied,
    ApprovalRequired,
)
from dare_framework3.utils.types import (
    ComponentType,
    PluginManagers,
    BaseComponent,
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

__all__ = [
    # ID generation
    "generate_id",
    # Errors
    "ToolError",
    "ToolNotFoundError",
    "ToolAccessDenied",
    "ApprovalRequired",
    # Types (from former builder/types.py)
    "ComponentType",
    "PluginManagers",
    "BaseComponent",
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
]
