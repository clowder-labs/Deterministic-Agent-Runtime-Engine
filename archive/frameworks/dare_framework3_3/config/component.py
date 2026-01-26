"""Config domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol


class IToolManager(Protocol):
    """[Component] Loads tool plugins (capability implementations).

    Usage: Called during agent setup to load tool instances.
    """

    def load_tools(self, *, config: Any | None = None) -> list[object]:
        """[Component] Load tool instances from configuration.

        Usage: Invoked by composition code to populate tool lists.
        """
        ...


class IModelAdapterManager(Protocol):
    """[Component] Loads the model adapter plugin.

    Usage: Called during agent setup to create a model adapter.
    """

    def load_model_adapter(self, *, config: Any | None = None) -> object | None:
        """[Component] Load the model adapter if configured.

        Usage: Invoked by composition code to choose an adapter.
        """
        ...


class IPlannerManager(Protocol):
    """[Component] Loads planning strategy plugins.

    Usage: Called during agent setup to select a planner.
    """

    def load_planner(self, *, config: Any | None = None) -> object | None:
        """[Component] Load a planner implementation.

        Usage: Invoked by composition code to select a planner.
        """
        ...


class IValidatorManager(Protocol):
    """[Component] Loads validator strategy plugins.

    Usage: Called during agent setup to select validators.
    """

    def load_validators(self, *, config: Any | None = None) -> list[object]:
        """[Component] Load validator implementations.

        Usage: Invoked by composition code to build validator lists.
        """
        ...


class IRemediatorManager(Protocol):
    """[Component] Loads remediation strategy plugins.

    Usage: Called during agent setup to select a remediator.
    """

    def load_remediator(self, *, config: Any | None = None) -> object | None:
        """[Component] Load a remediator implementation.

        Usage: Invoked by composition code to select remediation.
        """
        ...


class IProtocolAdapterManager(Protocol):
    """[Component] Loads protocol adapter plugins.

    Usage: Called during agent setup to connect external protocols.
    """

    def load_protocol_adapters(self, *, config: Any | None = None) -> list[object]:
        """[Component] Load protocol adapters.

        Usage: Invoked by composition code to attach adapters.
        """
        ...


class IHookManager(Protocol):
    """[Component] Loads hook plugins for the extension point.

    Usage: Called during agent setup to register hooks.
    """

    def load_hooks(self, *, config: Any | None = None) -> list[object]:
        """[Component] Load hook implementations.

        Usage: Invoked by composition code to register hooks.
        """
        ...


class IConfigProviderManager(Protocol):
    """[Component] Loads configuration provider plugins.

    Usage: Called during setup to resolve layered config sources.
    """

    def load_config_provider(self, *, config: Any | None = None) -> object | None:
        """[Component] Load a configuration provider.

        Usage: Invoked by composition code to select config sources.
        """
        ...


class IMemoryManager(Protocol):
    """[Component] Loads memory capability plugins.

    Usage: Called during agent setup to attach memory components.
    """

    def load_memory(self, *, config: Any | None = None) -> object | None:
        """[Component] Load the memory implementation.

        Usage: Invoked by composition code to attach memory.
        """
        ...


class IPromptStoreManager(Protocol):
    """[Component] Loads prompt store plugins.

    Usage: Called during agent setup to attach prompt stores.
    """

    def load_prompt_store(self, *, config: Any | None = None) -> object | None:
        """[Component] Load the prompt store implementation.

        Usage: Invoked by composition code to attach a prompt store.
        """
        ...


class ISkillManager(Protocol):
    """[Component] Loads skill plugins.

    Usage: Called during agent setup to attach skills.
    """

    def load_skills(self, *, config: Any | None = None) -> list[object]:
        """[Component] Load skill implementations.

        Usage: Invoked by composition code to attach skills.
        """
        ...


__all__ = [
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
