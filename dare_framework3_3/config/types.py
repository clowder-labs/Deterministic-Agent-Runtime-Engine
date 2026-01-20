"""[Types] Config domain data types and plugin metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dare_framework3_3.config.component import (
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


def _default_workspace_roots() -> list[str]:
    """Return the default workspace roots (current working directory)."""
    return [str(Path.cwd().resolve())]


class ComponentType(Enum):
    """Component category taxonomy used for configuration scoping.

    Values correspond to different pluggable component types
    that can be discovered and loaded via the plugin system.
    """

    PLANNER = "planner"
    VALIDATOR = "validator"
    REMEDIATOR = "remediator"
    MEMORY = "memory"
    MODEL_ADAPTER = "model_adapter"
    TOOL = "tool"
    SKILL = "skill"
    MCP = "mcp"
    HOOK = "hook"
    PROTOCOL_ADAPTER = "protocol_adapter"
    CONFIG_PROVIDER = "config_provider"
    PROMPT_STORE = "prompt_store"


@dataclass(frozen=True)
class PluginManagers:
    """Convenience container for plugin manager interfaces.

    Managers are loaded by config composition code and passed into agents.
    """

    tools: "IToolManager | None" = None
    model_adapters: "IModelAdapterManager | None" = None
    planners: "IPlannerManager | None" = None
    validators: "IValidatorManager | None" = None
    remediators: "IRemediatorManager | None" = None
    protocol_adapters: "IProtocolAdapterManager | None" = None
    hooks: "IHookManager | None" = None
    config_providers: "IConfigProviderManager | None" = None
    memory: "IMemoryManager | None" = None
    prompt_stores: "IPromptStoreManager | None" = None
    skills: "ISkillManager | None" = None


@dataclass(frozen=True)
class LLMConfig:
    """Connectivity settings for LLM backends.
    
    Attributes:
        adapter: Model adapter name (e.g., "openai", "mock")
        endpoint: API endpoint URL
        api_key: API authentication key
        model: Model name (e.g., "gpt-4o", "gpt-4o-mini")
        extra: Additional adapter-specific settings
    """
    adapter: str | None = None
    endpoint: str | None = None
    api_key: str | None = None
    model: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        """Create from a dictionary."""
        adapter = data.get("adapter")
        endpoint = data.get("endpoint")
        api_key = data.get("api_key")
        model = data.get("model")
        extra = {
            key: value
            for key, value in data.items()
            if key not in {"adapter", "endpoint", "api_key", "model"}
        }
        return cls(
            adapter=adapter,
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        payload: dict[str, Any] = {}
        if self.adapter is not None:
            payload["adapter"] = self.adapter
        if self.endpoint is not None:
            payload["endpoint"] = self.endpoint
        if self.api_key is not None:
            payload["api_key"] = self.api_key
        if self.model is not None:
            payload["model"] = self.model
        payload.update(self.extra)
        return payload


@dataclass(frozen=True)
class ComponentConfig:
    """Per-component-type configuration.
    
    Attributes:
        disabled: List of disabled component names
        entries: Named component configurations
    """
    disabled: list[str] = field(default_factory=list)
    entries: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComponentConfig":
        """Create from a dictionary."""
        disabled_raw = data.get("disabled", [])
        disabled = [str(item) for item in disabled_raw] if isinstance(disabled_raw, list) else []
        entries = {key: value for key, value in data.items() if key != "disabled"}
        return cls(disabled=disabled, entries=entries)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        payload = dict(self.entries)
        if self.disabled:
            payload["disabled"] = list(self.disabled)
        return payload


@dataclass(frozen=True)
class Config:
    """Effective configuration resolved from layered JSON sources.
    
    This is a Layer 3 convenience model; the Kernel remains config-schema agnostic.
    
    Attributes:
        llm: LLM backend configuration
        mcp: MCP server configurations
        tools: Tool-specific configurations
        allowtools: Allow-listed tool names
        allowmcps: Allow-listed MCP server names
        components: Per-component-type configurations
        workspace_roots: Allowed workspace directories
    """
    llm: LLMConfig = field(default_factory=LLMConfig)
    mcp: dict[str, dict[str, Any]] = field(default_factory=dict)
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
    allowtools: list[str] = field(default_factory=list)
    allowmcps: list[str] = field(default_factory=list)
    components: dict[str, ComponentConfig] = field(default_factory=dict)
    workspace_roots: list[str] = field(default_factory=_default_workspace_roots)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create from a dictionary."""
        llm_data = data.get("llm")
        llm = LLMConfig.from_dict(llm_data) if isinstance(llm_data, dict) else LLMConfig()
        mcp = data.get("mcp") if isinstance(data.get("mcp"), dict) else {}
        tools = data.get("tools") if isinstance(data.get("tools"), dict) else {}
        allowtools = data.get("allowtools") if isinstance(data.get("allowtools"), list) else []
        allowmcps = data.get("allowmcps") if isinstance(data.get("allowmcps"), list) else []
        components_raw = data.get("components") if isinstance(data.get("components"), dict) else {}
        components = {
            key: ComponentConfig.from_dict(value)
            for key, value in components_raw.items()
            if isinstance(value, dict)
        }
        workspace_roots_raw = data.get("workspace_roots")
        if isinstance(workspace_roots_raw, list):
            workspace_roots = [str(item) for item in workspace_roots_raw]
        else:
            workspace_roots = _default_workspace_roots()
        return cls(
            llm=llm,
            mcp=mcp,
            tools=tools,
            allowtools=allowtools,
            allowmcps=allowmcps,
            components=components,
            workspace_roots=workspace_roots,
        )

    def component_settings(self, component_type: str) -> ComponentConfig:
        """Get settings for a component type."""
        return self.components.get(component_type, ComponentConfig())

    def is_component_enabled(self, component_type: str, name: str) -> bool:
        """Check if a component is enabled."""
        settings = self.component_settings(component_type)
        return name not in settings.disabled

    def component_config(self, component_type: str, name: str) -> Any | None:
        """Get configuration for a specific component."""
        settings = self.component_settings(component_type)
        return settings.entries.get(name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        return {
            "llm": self.llm.to_dict(),
            "mcp": dict(self.mcp),
            "tools": dict(self.tools),
            "allowtools": list(self.allowtools),
            "allowmcps": list(self.allowmcps),
            "components": {key: value.to_dict() for key, value in self.components.items()},
            "workspace_roots": list(self.workspace_roots),
        }
