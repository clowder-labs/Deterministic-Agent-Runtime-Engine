"""Builder domain types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from dare_framework2.contracts import ComponentType

# =============================================================================
# Plugin Manager Interfaces
# =============================================================================

class IToolManager(Protocol):
    """Loads tool plugins (capability implementations)."""
    def load_tools(self, *, config: Any | None = None) -> list[object]: ...


class IModelAdapterManager(Protocol):
    """Loads the model adapter plugin."""
    def load_model_adapter(self, *, config: Any | None = None) -> object | None: ...


class IPlannerManager(Protocol):
    """Loads planning strategy plugins."""
    def load_planner(self, *, config: Any | None = None) -> object | None: ...


class IValidatorManager(Protocol):
    """Loads validator strategy plugins."""
    def load_validators(self, *, config: Any | None = None) -> list[object]: ...


class IRemediatorManager(Protocol):
    """Loads remediation strategy plugins."""
    def load_remediator(self, *, config: Any | None = None) -> object | None: ...


class IProtocolAdapterManager(Protocol):
    """Loads protocol adapter plugins."""
    def load_protocol_adapters(self, *, config: Any | None = None) -> list[object]: ...


class IHookManager(Protocol):
    """Loads hook plugins for the Kernel extension point."""
    def load_hooks(self, *, config: Any | None = None) -> list[object]: ...


class IMemoryManager(Protocol):
    """Loads memory capability plugins."""
    def load_memory(self, *, config: Any | None = None) -> object | None: ...


class IPromptStoreManager(Protocol):
    """Loads prompt store plugins."""
    def load_prompt_store(self, *, config: Any | None = None) -> object | None: ...


class ISkillManager(Protocol):
    """Loads skill plugins."""
    def load_skills(self, *, config: Any | None = None) -> list[object]: ...


@dataclass(frozen=True)
class PluginManagers:
    """A convenience container for passing managers into the builder.
    
    Each manager's behavior is defined by its own interface contract.
    """
    tools: IToolManager | None = None
    model_adapters: IModelAdapterManager | None = None
    planners: IPlannerManager | None = None
    validators: IValidatorManager | None = None
    remediators: IRemediatorManager | None = None
    protocol_adapters: IProtocolAdapterManager | None = None
    hooks: IHookManager | None = None
    memory: IMemoryManager | None = None
    prompt_stores: IPromptStoreManager | None = None
    skills: ISkillManager | None = None


# =============================================================================
# Base Component
# =============================================================================

class BaseComponent:
    """Base class for pluggable components.
    
    Provides common functionality for components that can be
    discovered and loaded via the plugin system.
    """
    order = 100

    @property
    def component_name(self) -> str:
        """Return the component name."""
        name = getattr(self, "name", None)
        if isinstance(name, str):
            return name
        return self.__class__.__name__

    async def init(
        self,
        config: object | None = None,
        prompts: object | None = None,
    ) -> None:
        """Initialize the component with configuration."""
        pass

    async def close(self) -> None:
        """Clean up component resources."""
        pass
