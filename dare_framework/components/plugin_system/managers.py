"""Component manager interfaces for entrypoint-based extensibility (v2).

This module defines interface positions only. Implementations MAY be no-ops in the
early v2 milestones, but the interfaces and docstrings must clearly communicate:
- what each manager is responsible for,
- the intended selection/filtering semantics (config-driven),
- and the design goal: deterministic, testable composition without Kernel coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class IToolManager(Protocol):
    """Loads tool plugins (capability implementations).

    Design goals:
    - Discover tools via the v2 entrypoint group (e.g., `dare_framework.v2.tools`).
    - Apply config filtering (allow/deny or disabled lists) deterministically.
    - Return a collection of tool instances; the ToolGateway/provider layer decides
      how to expose them as capabilities.
    """

    def load_tools(self, *, config: Any | None = None) -> list[object]: ...


class IModelAdapterManager(Protocol):
    """Loads the model adapter plugin used for model-driven execution.

    Semantics (intended):
    - Model adapters are **single-select**: select exactly the configured component name
      (entrypoint name), or return None when not configured.
    - If a name is configured but missing, implementations SHOULD fail fast to avoid
      silent fallbacks that hide misconfiguration.
    """

    def load_model_adapter(self, *, config: Any | None = None) -> object | None: ...


class IPlannerManager(Protocol):
    """Loads planning strategy plugins.

    Intended semantics:
    - Planners are typically single-select (one planner drives plan generation).
    - Config selects which planner implementation to use; defaults should be explicit.
    """

    def load_planner(self, *, config: Any | None = None) -> object | None: ...


class IValidatorManager(Protocol):
    """Loads validator strategy plugins.

    Semantics (intended):
    - Validators are **multi-load**: discover all validators, filter via config, then
      sort by `order` (ascending) and return a collection.
    - The builder/orchestrator may compose the collection into a single validator.
    """

    def load_validators(self, *, config: Any | None = None) -> list[object]: ...


class IRemediatorManager(Protocol):
    """Loads remediation strategy plugins.

    Intended semantics:
    - Remediators are typically single-select (one remediator decides reflection).
    - Config selects which remediator implementation to use; a no-op remediator is a
      valid default for MVP.
    """

    def load_remediator(self, *, config: Any | None = None) -> object | None: ...


class IProtocolAdapterManager(Protocol):
    """Loads protocol adapter plugins (Layer 1).

    Intended semantics:
    - Protocol adapters are usually multi-load (multiple capability sources).
    - Config selects endpoints/enablement; adapters translate protocol → capabilities.
    """

    def load_protocol_adapters(self, *, config: Any | None = None) -> list[object]: ...


class IHookManager(Protocol):
    """Loads hook plugins for the Kernel extension point.

    Intended semantics:
    - Hooks are multi-load, ordered, and best-effort by default.
    - Manager returns a collection of hook callables or hook objects that can be
      registered into `IExtensionPoint`.
    """

    def load_hooks(self, *, config: Any | None = None) -> list[object]: ...


class IConfigProviderManager(Protocol):
    """Loads configuration provider plugins.

    Intended semantics:
    - Config providers are single-select or ordered chain (implementation-defined).
    - A provider yields an effective config snapshot for the session/build.
    """

    def load_config_provider(self, *, config: Any | None = None) -> object | None: ...


# Optional placeholders (reserved for future capabilities).
class IMemoryManager(Protocol):
    """Loads memory capability plugins (optional in early v2 milestones)."""

    def load_memory(self, *, config: Any | None = None) -> object | None: ...


class IPromptStoreManager(Protocol):
    """Loads prompt store plugins (optional in early v2 milestones)."""

    def load_prompt_store(self, *, config: Any | None = None) -> object | None: ...


class ISkillManager(Protocol):
    """Loads skill plugins (plan-time macros; optional in early v2 milestones)."""

    def load_skills(self, *, config: Any | None = None) -> list[object]: ...


@dataclass(frozen=True)
class PluginManagers:
    """A convenience container for passing managers into the builder.

    This is intentionally a thin data holder. Each manager's behavior is defined by
    its own interface contract and documentation.
    """

    tools: IToolManager | None = None
    model_adapters: IModelAdapterManager | None = None
    planners: IPlannerManager | None = None
    validators: IValidatorManager | None = None
    remediators: IRemediatorManager | None = None
    protocol_adapters: IProtocolAdapterManager | None = None
    hooks: IHookManager | None = None
    config_providers: IConfigProviderManager | None = None
    memory: IMemoryManager | None = None
    prompt_stores: IPromptStoreManager | None = None
    skills: ISkillManager | None = None


class NoOpToolManager:
    """No-op tool manager used as a safe default placeholder."""

    def load_tools(self, *, config: Any | None = None) -> list[object]:
        return []


class NoOpModelAdapterManager:
    """No-op model adapter manager used as a safe default placeholder."""

    def load_model_adapter(self, *, config: Any | None = None) -> object | None:
        return None


class NoOpPlannerManager:
    """No-op planner manager used as a safe default placeholder."""

    def load_planner(self, *, config: Any | None = None) -> object | None:
        return None


class NoOpValidatorManager:
    """No-op validator manager used as a safe default placeholder."""

    def load_validators(self, *, config: Any | None = None) -> list[object]:
        return []


class NoOpRemediatorManager:
    """No-op remediator manager used as a safe default placeholder."""

    def load_remediator(self, *, config: Any | None = None) -> object | None:
        return None


class NoOpProtocolAdapterManager:
    """No-op protocol adapter manager used as a safe default placeholder."""

    def load_protocol_adapters(self, *, config: Any | None = None) -> list[object]:
        return []


class NoOpHookManager:
    """No-op hook manager used as a safe default placeholder."""

    def load_hooks(self, *, config: Any | None = None) -> list[object]:
        return []


class NoOpConfigProviderManager:
    """No-op config provider manager used as a safe default placeholder."""

    def load_config_provider(self, *, config: Any | None = None) -> object | None:
        return None


class NoOpMemoryManager:
    """No-op memory manager used as a safe default placeholder."""

    def load_memory(self, *, config: Any | None = None) -> object | None:
        return None


class NoOpPromptStoreManager:
    """No-op prompt store manager used as a safe default placeholder."""

    def load_prompt_store(self, *, config: Any | None = None) -> object | None:
        return None


class NoOpSkillManager:
    """No-op skill manager used as a safe default placeholder."""

    def load_skills(self, *, config: Any | None = None) -> list[object]:
        return []
