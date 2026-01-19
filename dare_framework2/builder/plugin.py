"""Plugin system helpers and no-op implementations."""

from __future__ import annotations

from typing import Any


# =============================================================================
# No-op Plugin Manager Implementations
# =============================================================================

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
