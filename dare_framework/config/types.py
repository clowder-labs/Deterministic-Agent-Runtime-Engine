"""Config domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dare_framework.infra.component import ComponentType
from dare_framework.infra.component import IComponent


def _default_workspace_dir() -> str:
    """Return the default workspace directory (project root when available)."""
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return str(cwd)


def _default_user_dir() -> str:
    """Return the default user directory (home directory)."""
    return str(Path.home().resolve())


@dataclass(frozen=True)
class ProxyConfig:
    """Proxy settings for outbound model adapter requests."""

    http: str | None = None
    https: str | None = None
    no_proxy: str | None = None
    use_system_proxy: bool = False
    disabled: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProxyConfig":
        """Create from a dictionary, enforcing precedence rules."""
        disabled = bool(data.get("disabled", False))
        use_system_proxy = bool(data.get("use_system_proxy", False))
        http = data.get("http")
        https = data.get("https")
        no_proxy = data.get("no_proxy")

        if disabled:
            return cls(disabled=True)
        if use_system_proxy:
            return cls(use_system_proxy=True)

        return cls(
            http=str(http) if http is not None else None,
            https=str(https) if https is not None else None,
            no_proxy=str(no_proxy) if no_proxy is not None else None,
        )

    def is_enabled(self) -> bool:
        """Return True when proxy configuration should be applied."""
        if self.disabled:
            return False
        return self.use_system_proxy or any([self.http, self.https, self.no_proxy])

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        payload: dict[str, Any] = {}
        if self.http is not None:
            payload["http"] = self.http
        if self.https is not None:
            payload["https"] = self.https
        if self.no_proxy is not None:
            payload["no_proxy"] = self.no_proxy
        if self.use_system_proxy:
            payload["use_system_proxy"] = self.use_system_proxy
        if self.disabled:
            payload["disabled"] = self.disabled
        return payload


@dataclass(frozen=True)
class LLMConfig:
    """Connectivity settings for LLM backends."""

    adapter: str | None = None
    endpoint: str | None = None
    api_key: str | None = None
    model: str | None = None
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        """Create from a dictionary."""
        adapter = data.get("adapter")
        endpoint = data.get("endpoint")
        api_key = data.get("api_key")
        model = data.get("model")
        proxy_raw = data.get("proxy")
        proxy = ProxyConfig.from_dict(proxy_raw) if isinstance(proxy_raw, dict) else ProxyConfig()
        extra = {
            key: value
            for key, value in data.items()
            if key not in {"adapter", "endpoint", "api_key", "model", "proxy"}
        }
        return cls(
            adapter=adapter,
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            proxy=proxy,
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
        proxy_payload = self.proxy.to_dict()
        if proxy_payload:
            payload["proxy"] = proxy_payload
        payload.update(self.extra)
        return payload


@dataclass(frozen=True)
class ComponentConfig:
    """Per-component-type configuration."""

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


def _component_key(component_type: ComponentType | str) -> str:
    """Normalize component type values for lookup."""
    if isinstance(component_type, ComponentType):
        return component_type.value
    return str(component_type)


@dataclass(frozen=True)
class Config:
    """Effective configuration resolved from layered sources."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    mcp: dict[str, dict[str, Any]] = field(default_factory=dict)
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
    allowtools: list[str] = field(default_factory=list)
    allowmcps: list[str] = field(default_factory=list)
    components: dict[str, ComponentConfig] = field(default_factory=dict)
    workspace_dir: str = field(default_factory=_default_workspace_dir)
    user_dir: str = field(default_factory=_default_user_dir)

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
        workspace_dir_raw = data.get("workspace_dir")
        if isinstance(workspace_dir_raw, str):
            workspace_dir = workspace_dir_raw
        else:
            workspace_roots_raw = data.get("workspace_roots")
            if isinstance(workspace_roots_raw, list) and workspace_roots_raw:
                workspace_dir = str(workspace_roots_raw[0])
            else:
                workspace_dir = _default_workspace_dir()
        user_dir_raw = data.get("user_dir")
        user_dir = user_dir_raw if isinstance(user_dir_raw, str) else _default_user_dir()
        return cls(
            llm=llm,
            mcp=mcp,
            tools=tools,
            allowtools=allowtools,
            allowmcps=allowmcps,
            components=components,
            workspace_dir=workspace_dir,
            user_dir=user_dir,
        )

    def component_settings(self, component_type: ComponentType | str) -> ComponentConfig:
        """Get settings for a component type."""
        return self.components.get(_component_key(component_type), ComponentConfig())

    def is_component_enabled_name(self, component_type: ComponentType | str, name: str) -> bool:
        """Check if a named component instance is enabled."""
        settings = self.component_settings(component_type)
        return name not in settings.disabled

    def is_component_enabled(self, component: IComponent) -> bool:
        """Check if a concrete component instance is enabled."""

        return self.is_component_enabled_name(component.component_type, component.name)

    def filter_enabled(self, components: list[IComponent]) -> list[IComponent]:
        """Filter a list of components, keeping only enabled ones."""

        return [component for component in components if self.is_component_enabled(component)]

    def component_config_name(self, component_type: ComponentType | str, name: str) -> Any | None:
        """Get configuration for a specific named component instance."""
        settings = self.component_settings(component_type)
        return settings.entries.get(name)

    def component_config(self, component: IComponent) -> Any | None:
        """Get per-component configuration for a concrete component instance."""

        return self.component_config_name(component.component_type, component.name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        return {
            "llm": self.llm.to_dict(),
            "mcp": dict(self.mcp),
            "tools": dict(self.tools),
            "allowtools": list(self.allowtools),
            "allowmcps": list(self.allowmcps),
            "components": {key: value.to_dict() for key, value in self.components.items()},
            "workspace_dir": self.workspace_dir,
            "user_dir": self.user_dir,
        }
__all__ = ["ComponentType", "ProxyConfig", "LLMConfig", "ComponentConfig", "Config"]
