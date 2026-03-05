"""Config domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

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
    def from_dict(cls, data: dict[str, Any]) -> ProxyConfig:
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
    def from_dict(cls, data: dict[str, Any]) -> LLMConfig:
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
    def from_dict(cls, data: dict[str, Any]) -> ComponentConfig:
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
class RedactionConfig:
    """Redaction policy for telemetry payloads."""

    mode: Literal["denylist", "allowlist"] = "denylist"
    keys: list[str] = field(default_factory=list)
    replacement: str = "[REDACTED]"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RedactionConfig:
        mode = data.get("mode", "denylist")
        if mode not in {"denylist", "allowlist"}:
            mode = "denylist"
        keys_raw = data.get("keys", [])
        keys = [str(item) for item in keys_raw] if isinstance(keys_raw, list) else []
        replacement = data.get("replacement")
        if replacement is None:
            replacement = "[REDACTED]"
        return cls(mode=mode, keys=keys, replacement=str(replacement))

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "keys": list(self.keys),
            "replacement": self.replacement,
        }


@dataclass(frozen=True)
class ObservabilityConfig:
    """Observability configuration for telemetry providers."""

    enabled: bool = False
    traces_enabled: bool = True
    metrics_enabled: bool = True
    logs_enabled: bool = False
    exporter: Literal["otlp", "console", "none"] = "none"
    otlp_endpoint: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    insecure: bool = False
    sampling_ratio: float = 1.0
    capture_content: bool = False
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    attribute_cardinality_limits: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObservabilityConfig:
        enabled = bool(data.get("enabled", False))
        traces_enabled = bool(data.get("traces_enabled", True))
        metrics_enabled = bool(data.get("metrics_enabled", True))
        logs_enabled = bool(data.get("logs_enabled", False))
        exporter = data.get("exporter", "none")
        if exporter not in {"otlp", "console", "none"}:
            exporter = "none"
        otlp_endpoint = data.get("otlp_endpoint")
        headers_raw = data.get("headers", {})
        headers = (
            {str(key): str(value) for key, value in headers_raw.items()}
            if isinstance(headers_raw, dict)
            else {}
        )
        insecure = bool(data.get("insecure", False))
        sampling_ratio_raw = data.get("sampling_ratio", 1.0)
        try:
            sampling_ratio = float(sampling_ratio_raw)
        except (TypeError, ValueError):
            sampling_ratio = 1.0
        sampling_ratio = max(0.0, min(1.0, sampling_ratio))
        capture_content = bool(data.get("capture_content", False))
        redaction_raw = data.get("redaction")
        redaction = (
            RedactionConfig.from_dict(redaction_raw)
            if isinstance(redaction_raw, dict)
            else RedactionConfig()
        )
        limits_raw = data.get("attribute_cardinality_limits", {})
        attribute_cardinality_limits = (
            {str(key): int(value) for key, value in limits_raw.items()}
            if isinstance(limits_raw, dict)
            else {}
        )
        return cls(
            enabled=enabled,
            traces_enabled=traces_enabled,
            metrics_enabled=metrics_enabled,
            logs_enabled=logs_enabled,
            exporter=exporter,
            otlp_endpoint=otlp_endpoint if otlp_endpoint is not None else None,
            headers=headers,
            insecure=insecure,
            sampling_ratio=sampling_ratio,
            capture_content=capture_content,
            redaction=redaction,
            attribute_cardinality_limits=attribute_cardinality_limits,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "enabled": self.enabled,
            "traces_enabled": self.traces_enabled,
            "metrics_enabled": self.metrics_enabled,
            "logs_enabled": self.logs_enabled,
            "exporter": self.exporter,
            "sampling_ratio": self.sampling_ratio,
            "capture_content": self.capture_content,
            "redaction": self.redaction.to_dict(),
            "attribute_cardinality_limits": dict(self.attribute_cardinality_limits),
        }
        if self.otlp_endpoint is not None:
            payload["otlp_endpoint"] = self.otlp_endpoint
        if self.headers:
            payload["headers"] = dict(self.headers)
        if self.insecure:
            payload["insecure"] = self.insecure
        return payload


@dataclass(frozen=True)
class CLIConfig:
    """CLI-specific runtime behavior."""

    log_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CLIConfig:
        raw_log_path = data.get("log_path")
        log_path = str(raw_log_path) if raw_log_path is not None else None
        return cls(log_path=log_path)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.log_path is not None:
            payload["log_path"] = self.log_path
        return payload


@dataclass(frozen=True)
class SystemPromptConfig:
    """Runtime system-prompt override policy."""

    mode: Literal["replace", "append"] | None = None
    content: str | None = None
    path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemPromptConfig:
        raw_mode = data.get("mode")
        mode: Literal["replace", "append"] | None = None
        if raw_mode is not None:
            normalized = str(raw_mode).strip().lower()
            if normalized not in {"replace", "append"}:
                raise ValueError(f"invalid system_prompt.mode: {raw_mode}")
            mode = "replace" if normalized == "replace" else "append"
        raw_content = data.get("content")
        content = str(raw_content) if raw_content is not None else None
        raw_path = data.get("path")
        path = str(raw_path) if raw_path is not None else None
        return cls(mode=mode, content=content, path=path)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.mode is not None:
            payload["mode"] = self.mode
        if self.content is not None:
            payload["content"] = self.content
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True)
class HooksConfig:
    """Governance configuration for runtime hook orchestration."""

    version: int = 1
    defaults: dict[str, Any] = field(default_factory=dict)
    entries: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HooksConfig:
        version_raw = data.get("version", 1)
        try:
            version = int(version_raw)
        except (TypeError, ValueError):
            version = 1
        defaults_raw = data.get("defaults")
        defaults = dict(defaults_raw) if isinstance(defaults_raw, dict) else {}
        entries_raw = data.get("entries")
        entries = [dict(item) for item in entries_raw if isinstance(item, dict)] if isinstance(entries_raw, list) else []
        return cls(version=version, defaults=defaults, entries=entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "defaults": dict(self.defaults),
            "entries": [dict(item) for item in self.entries],
        }

    def priority_for(self, hook_name: str, *, default: int = 100) -> int:
        """Resolve configured hook priority by hook name."""

        for entry in self.entries:
            if str(entry.get("name", "")) != hook_name:
                continue
            raw = entry.get("priority", self.defaults.get("priority", default))
            try:
                return int(raw)
            except (TypeError, ValueError):
                return default
        raw_default = self.defaults.get("priority", default)
        try:
            return int(raw_default)
        except (TypeError, ValueError):
            return default


@dataclass(frozen=True)
class EventLogConfig:
    """Default event-log wiring policy for runtime builders."""

    enabled: bool = False
    path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventLogConfig:
        enabled = bool(data.get("enabled", False))
        raw_path = data.get("path")
        path = str(raw_path) if raw_path is not None else None
        return cls(enabled=enabled, path=path)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"enabled": self.enabled}
        if self.path is not None:
            payload["path"] = self.path
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
    mcp_paths: list[str] = field(default_factory=list)
    """Directories to scan for MCP config files (e.g. .dare/mcp)."""
    skill_paths: list[str] = field(default_factory=list)
    """Directories to scan for skills (SKILL.md). When non-empty, used by SkillStoreBuilder; else default .dare/skills."""
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
    cli: CLIConfig = field(default_factory=CLIConfig)
    system_prompt: SystemPromptConfig = field(default_factory=SystemPromptConfig)
    allow_tools: list[str] = field(default_factory=list)
    allow_mcps: list[str] = field(default_factory=list)
    components: dict[str, ComponentConfig] = field(default_factory=dict)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    event_log: EventLogConfig = field(default_factory=EventLogConfig)
    security: dict[str, Any] = field(default_factory=dict)
    knowledge: dict[str, Any] = field(default_factory=dict)
    """Knowledge backend config: type (vector|rawdata), storage (in_memory|sqlite|chromadb), options."""
    long_term_memory: dict[str, Any] = field(default_factory=dict)
    """Long-term memory backend config: type (vector|rawdata), storage (in_memory|sqlite|chromadb), options."""
    workspace_dir: str = field(default_factory=_default_workspace_dir)
    user_dir: str = field(default_factory=_default_user_dir)
    prompt_store_path_pattern: str = ".dare/_prompts.json"
    default_prompt_id: str | None = None
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create from a dictionary."""
        llm_data = data.get("llm")
        llm = LLMConfig.from_dict(llm_data) if isinstance(llm_data, dict) else LLMConfig()
        mcp = data.get("mcp") if isinstance(data.get("mcp"), dict) else {}
        mcp_paths_raw = data.get("mcp_paths")
        mcp_paths = (
            [str(p) for p in mcp_paths_raw]
            if isinstance(mcp_paths_raw, list)
            else []
        )
        skill_paths_raw = data.get("skill_paths")
        skill_paths = (
            [str(p) for p in skill_paths_raw]
            if isinstance(skill_paths_raw, list)
            else []
        )
        tools = data.get("tools") if isinstance(data.get("tools"), dict) else {}
        cli_raw = data.get("cli")
        cli = CLIConfig.from_dict(cli_raw) if isinstance(cli_raw, dict) else CLIConfig()
        system_prompt_raw = data.get("system_prompt")
        system_prompt = (
            SystemPromptConfig.from_dict(system_prompt_raw)
            if isinstance(system_prompt_raw, dict)
            else SystemPromptConfig()
        )
        allow_tools = [str(item) for item in data.get("allow_tools", [])] if isinstance(data.get("allow_tools"), list) else []
        allow_mcps = [str(item) for item in data.get("allow_mcps", [])] if isinstance(data.get("allow_mcps"), list) else []
        components_raw = data.get("components") if isinstance(data.get("components"), dict) else {}
        components = {
            key: ComponentConfig.from_dict(value)
            for key, value in components_raw.items()
            if isinstance(value, dict)
        }
        hooks_raw = data.get("hooks")
        hooks = HooksConfig.from_dict(hooks_raw) if isinstance(hooks_raw, dict) else HooksConfig()
        event_log_raw = data.get("event_log")
        event_log = (
            EventLogConfig.from_dict(event_log_raw)
            if isinstance(event_log_raw, dict)
            else EventLogConfig()
        )
        security = data.get("security") if isinstance(data.get("security"), dict) else {}
        knowledge = data.get("knowledge") if isinstance(data.get("knowledge"), dict) else {}
        long_term_memory = data.get("long_term_memory") if isinstance(data.get("long_term_memory"), dict) else {}
        prompt_store_path_pattern = data.get("prompt_store_path_pattern")
        if not isinstance(prompt_store_path_pattern, str) or not prompt_store_path_pattern:
            prompt_store_path_pattern = ".dare/_prompts.json"
        default_prompt_id = data.get("default_prompt_id")
        if default_prompt_id is not None:
            default_prompt_id = str(default_prompt_id)
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
        observability_raw = data.get("observability")
        observability = (
            ObservabilityConfig.from_dict(observability_raw)
            if isinstance(observability_raw, dict)
            else ObservabilityConfig()
        )
        return cls(
            llm=llm,
            mcp=mcp,
            mcp_paths=mcp_paths,
            skill_paths=skill_paths,
            tools=tools,
            cli=cli,
            system_prompt=system_prompt,
            allow_tools=allow_tools,
            allow_mcps=allow_mcps,
            components=components,
            hooks=hooks,
            event_log=event_log,
            security=security,
            knowledge=knowledge,
            long_term_memory=long_term_memory,
            workspace_dir=workspace_dir,
            user_dir=user_dir,
            prompt_store_path_pattern=prompt_store_path_pattern,
            default_prompt_id=default_prompt_id,
            observability=observability,
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
            "mcp_paths": list(self.mcp_paths),
            "skill_paths": list(self.skill_paths),
            "tools": dict(self.tools),
            "cli": self.cli.to_dict(),
            "system_prompt": self.system_prompt.to_dict(),
            "allow_tools": list(self.allow_tools),
            "allow_mcps": list(self.allow_mcps),
            "components": {key: value.to_dict() for key, value in self.components.items()},
            "hooks": self.hooks.to_dict(),
            "event_log": self.event_log.to_dict(),
            "security": dict(self.security),
            "knowledge": dict(self.knowledge),
            "long_term_memory": dict(self.long_term_memory),
            "workspace_dir": self.workspace_dir,
            "user_dir": self.user_dir,
            "prompt_store_path_pattern": self.prompt_store_path_pattern,
            "default_prompt_id": self.default_prompt_id,
            "observability": self.observability.to_dict(),
        }
__all__ = [
    "CLIConfig",
    "ProxyConfig",
    "LLMConfig",
    "SystemPromptConfig",
    "ComponentConfig",
    "HooksConfig",
    "EventLogConfig",
    "RedactionConfig",
    "ObservabilityConfig",
    "Config",
]
