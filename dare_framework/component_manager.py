from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata
from typing import Any, Callable

from .core.interfaces import (
    IComponent,
    IComponentRegistrar,
    IConfigProvider,
    IHook,
    IMCPClient,
    IMemory,
    IModelAdapter,
    IPromptStore,
    ISkill,
    ITool,
    IValidator,
)
from .components.registries import SkillRegistry, ToolRegistry

EntryPointLoader = Callable[[], Any]

DEFAULT_ENTRYPOINT_GROUPS = {
    "validators": "dare_framework.validators",
    "memory": "dare_framework.memory",
    "model_adapters": "dare_framework.model_adapters",
    "tools": "dare_framework.tools",
    "skills": "dare_framework.skills",
    "mcp_clients": "dare_framework.mcp_clients",
    "hooks": "dare_framework.hooks",
    "config_providers": "dare_framework.config_providers",
    "prompt_stores": "dare_framework.prompt_stores",
}


@dataclass
class ComponentDiscoveryConfig:
    enabled: bool = True
    groups: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ENTRYPOINT_GROUPS))
    include: set[str] | None = None
    exclude: set[str] | None = None


class ComponentManager(IComponentRegistrar):
    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        discovery_config: ComponentDiscoveryConfig | None = None,
        entry_points_loader: EntryPointLoader | None = None,
    ) -> None:
        self._tool_registry = tool_registry or ToolRegistry()
        self._skill_registry = skill_registry or SkillRegistry()
        self._discovery_config = discovery_config or ComponentDiscoveryConfig()
        self._entry_points_loader = entry_points_loader or metadata.entry_points
        self._registered_ids: set[int] = set()
        self._owned_components: list[IComponent] = []
        self._external_components: list[IComponent] = []
        self._validators: list[IValidator] = []
        self._model_adapters: list[IModelAdapter] = []
        self._memories: list[IMemory] = []
        self._mcp_clients: list[IMCPClient] = []
        self._hooks: list[IHook] = []
        self._config_providers: list[IConfigProvider] = []
        self._prompt_stores: list[IPromptStore] = []

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    @property
    def skill_registry(self) -> SkillRegistry:
        return self._skill_registry

    @property
    def validators(self) -> list[IValidator]:
        return list(self._validators)

    @property
    def model_adapters(self) -> list[IModelAdapter]:
        return list(self._model_adapters)

    @property
    def memories(self) -> list[IMemory]:
        return list(self._memories)

    @property
    def mcp_clients(self) -> list[IMCPClient]:
        return list(self._mcp_clients)

    @property
    def hooks(self) -> list[IHook]:
        return list(self._hooks)

    @property
    def config_providers(self) -> list[IConfigProvider]:
        return list(self._config_providers)

    @property
    def prompt_stores(self) -> list[IPromptStore]:
        return list(self._prompt_stores)

    async def load(self) -> None:
        components = self._discover_components()
        ordered = sorted(components, key=lambda comp: getattr(comp, "order", 100))
        default_config: IConfigProvider | None = None
        default_prompts: IPromptStore | None = None
        for component in ordered:
            await component.init(default_config, default_prompts)
            component.register(self)
            self._record_owned(component)
            if isinstance(component, IConfigProvider) and default_config is None:
                default_config = component
            if isinstance(component, IPromptStore) and default_prompts is None:
                default_prompts = component

    async def close(self) -> None:
        for component in self._owned_components:
            await component.close()

    def register_component(self, component: IComponent) -> None:
        component_id = id(component)
        if component_id in self._registered_ids:
            return
        self._registered_ids.add(component_id)

        if isinstance(component, ITool):
            self._tool_registry.register_tool(component)
        if isinstance(component, ISkill):
            self._skill_registry.register_skill(component)
        if isinstance(component, IValidator):
            self._validators.append(component)
        if isinstance(component, IModelAdapter):
            self._model_adapters.append(component)
        if isinstance(component, IMemory):
            self._memories.append(component)
        if isinstance(component, IMCPClient):
            self._mcp_clients.append(component)
        if isinstance(component, IHook):
            self._hooks.append(component)
        if isinstance(component, IConfigProvider):
            self._config_providers.append(component)
        if isinstance(component, IPromptStore):
            self._prompt_stores.append(component)

    def add_component(self, component: IComponent) -> None:
        component.register(self)
        self._external_components.append(component)

    def _record_owned(self, component: IComponent) -> None:
        self._owned_components.append(component)

    def _discover_components(self) -> list[IComponent]:
        config = self._discovery_config
        if not config.enabled:
            return []
        discovered: list[IComponent] = []
        for group in config.groups.values():
            for entry_point in self._iter_entry_points(group):
                name = entry_point.name
                if config.include and name not in config.include:
                    continue
                if config.exclude and name in config.exclude:
                    continue
                component = self._load_entry_point(entry_point)
                if component is not None:
                    discovered.append(component)
        return discovered

    def _iter_entry_points(self, group: str):
        entry_points = self._entry_points_loader()
        if hasattr(entry_points, "select"):
            return list(entry_points.select(group=group))
        return list(entry_points.get(group, []))

    def _load_entry_point(self, entry_point) -> IComponent | None:
        loaded = entry_point.load()
        if isinstance(loaded, type):
            return loaded()
        if callable(loaded):
            return loaded()
        return None
