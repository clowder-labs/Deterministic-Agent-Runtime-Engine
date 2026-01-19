from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dare_framework.config.component_config import ComponentConfig
from dare_framework.config.llm_config import LLMConfig
from dare_framework.components.plugin_system.component_type import ComponentType


def _default_workspace_roots() -> list[str]:
    return [str(Path.cwd().resolve())]


@dataclass(frozen=True)
class Config:
    """Effective configuration resolved from layered JSON sources.

    Notes:
    - This is a Layer 3 convenience model; the Kernel remains config-schema agnostic.
    - Plugin managers MAY use this for deterministic selection/filtering.
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

    def component_settings(self, component_type: ComponentType) -> ComponentConfig:
        return self.components.get(component_type.value, ComponentConfig())

    def is_component_enabled(self, component_type: ComponentType, name: str) -> bool:
        settings = self.component_settings(component_type)
        return name not in settings.disabled

    def component_config(self, component_type: ComponentType, name: str) -> Any | None:
        settings = self.component_settings(component_type)
        return settings.entries.get(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm": self.llm.to_dict(),
            "mcp": dict(self.mcp),
            "tools": dict(self.tools),
            "allowtools": list(self.allowtools),
            "allowmcps": list(self.allowmcps),
            "components": {key: value.to_dict() for key, value in self.components.items()},
            "workspace_roots": list(self.workspace_roots),
        }
