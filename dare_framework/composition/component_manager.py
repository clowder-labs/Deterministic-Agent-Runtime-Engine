from __future__ import annotations

from importlib import metadata
from typing import Any, Callable, Generic, TypeVar

from ..components.registries import SkillRegistry, ToolRegistry
from ..core.composition import IComponent, IComponentRegistrar, IConfigurableComponent
from ..core.config import IConfigProvider, IPromptStore
from ..core.context import IMemory, IModelAdapter
from ..core.mcp import IMCPClient
from ..core.runtime import IHook
from ..core.tooling import ISkill, ITool
from ..core.validation import IValidator
from ..core.models.config import Config

EntryPointLoader = Callable[[], Any]
TComponent = TypeVar("TComponent", bound=IComponent)

ENTRYPOINT_VALIDATORS = "dare_framework.validators"
ENTRYPOINT_MEMORY = "dare_framework.memory"
ENTRYPOINT_MODEL_ADAPTERS = "dare_framework.model_adapters"
ENTRYPOINT_TOOLS = "dare_framework.tools"
ENTRYPOINT_SKILLS = "dare_framework.skills"
ENTRYPOINT_MCP_CLIENTS = "dare_framework.mcp_clients"
ENTRYPOINT_HOOKS = "dare_framework.hooks"
ENTRYPOINT_CONFIG_PROVIDERS = "dare_framework.config_providers"
ENTRYPOINT_PROMPT_STORES = "dare_framework.prompt_stores"


class BaseComponentManager(IComponentRegistrar, Generic[TComponent]):
    def __init__(
        self,
        entrypoint_group: str,
        expected_type: type[TComponent],
        entry_points_loader: EntryPointLoader | None = None,
        config_section: str | None = None,
    ) -> None:
        self._entrypoint_group = entrypoint_group
        self._expected_type = expected_type
        self._entry_points_loader = entry_points_loader or metadata.entry_points
        self._components: list[TComponent] = []
        self._registered_ids: set[int] = set()
        self._config_section = config_section

    async def load(
        self,
        config: Config | None,
        prompt_store: IPromptStore | None = None,
    ) -> list[TComponent]:
        discovered = self._discover_components()
        if config_provider is not None:
            discovered = self._apply_component_filters(discovered, config_provider)
        ordered = sorted(discovered, key=lambda comp: getattr(comp, "order", 100))
        for component in ordered:
            if not self._is_enabled(component, config):
                continue
            await component.init(config, prompt_store)
            component.register(self)
        return list(self._components)

    def _is_enabled(self, component: TComponent, config: Config | None) -> bool:
        if config is None or not isinstance(component, IConfigurableComponent):
            return True
        return config.is_component_enabled(component.component_type, component.component_name)

    def register_component(self, component: IComponent) -> None:
        if not isinstance(component, self._expected_type):
            return
        component_id = id(component)
        if component_id in self._registered_ids:
            return
        self._registered_ids.add(component_id)
        typed_component = component
        self._components.append(typed_component)
        self._register_component(typed_component)

    def _register_component(self, component: TComponent) -> None:
        return None

    def _discover_components(self) -> list[TComponent]:
        entry_points = self._entry_points_loader()
        if hasattr(entry_points, "select"):
            group_entries = list(entry_points.select(group=self._entrypoint_group))
        else:
            group_entries = list(entry_points.get(self._entrypoint_group, []))

        components: list[TComponent] = []
        for entry_point in group_entries:
            component = self._load_entry_point(entry_point)
            if component is not None:
                components.append(component)
        return components

    def _load_entry_point(self, entry_point) -> TComponent | None:
        loaded = entry_point.load()
        if isinstance(loaded, type):
            instance = loaded()
        elif callable(loaded):
            instance = loaded()
        else:
            return None
        if not isinstance(instance, self._expected_type):
            return None
        return instance

    def _apply_component_filters(
        self,
        components: list[TComponent],
        config_provider: IConfigProvider,
    ) -> list[TComponent]:
        if not self._config_section:
            return components
        config = config_provider.get_namespace(self._config_section)
        enable_list = set(config.get("enable", [])) if isinstance(config, dict) else set()
        disable_list = set(config.get("disable", [])) if isinstance(config, dict) else set()
        filtered: list[TComponent] = []
        for component in components:
            name = getattr(component, "name", component.__class__.__name__)
            if enable_list and name not in enable_list:
                continue
            if name in disable_list:
                continue
            filtered.append(component)
        return filtered


class ValidatorManager(BaseComponentManager[IValidator]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_VALIDATORS, IValidator, entry_points_loader, config_section="validators")


class MemoryManager(BaseComponentManager[IMemory]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_MEMORY, IMemory, entry_points_loader, config_section="memory")


class ModelAdapterManager(BaseComponentManager[IModelAdapter]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_MODEL_ADAPTERS, IModelAdapter, entry_points_loader, config_section="llm")


class ToolManager(BaseComponentManager[ITool]):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        entry_points_loader: EntryPointLoader | None = None,
    ) -> None:
        super().__init__(ENTRYPOINT_TOOLS, ITool, entry_points_loader, config_section="tools")
        self._tool_registry = tool_registry

    def _register_component(self, component: ITool) -> None:
        self._tool_registry.register_tool(component)

    async def load(
        self,
        config_provider: IConfigProvider | None,
        prompt_store: IPromptStore | None = None,
    ) -> list[ITool]:
        components = await super().load(config_provider, prompt_store)
        if config_provider is not None:
            self._register_composite_tools(config_provider)
        return list(self._components)

    def _register_composite_tools(self, config_provider: IConfigProvider) -> None:
        composite_config = config_provider.get("composite_tools", [])
        if isinstance(composite_config, dict):
            composite_config = composite_config.get("tools", [])
        if not isinstance(composite_config, list):
            return
        from .components.composite_tool import CompositeTool  # type: ignore

        for recipe in composite_config:
            if not isinstance(recipe, dict):
                continue
            name = recipe.get("name")
            steps = recipe.get("steps", [])
            if not name or not isinstance(steps, list):
                continue
            description = recipe.get("description", "")
            composite = CompositeTool(name=name, description=description, steps=steps, toolkit=self._tool_registry)
            self.register_component(composite)


class SkillManager(BaseComponentManager[ISkill]):
    def __init__(
        self,
        skill_registry: SkillRegistry,
        entry_points_loader: EntryPointLoader | None = None,
    ) -> None:
        super().__init__(ENTRYPOINT_SKILLS, ISkill, entry_points_loader, config_section="skills")
        self._skill_registry = skill_registry

    def _register_component(self, component: ISkill) -> None:
        self._skill_registry.register_skill(component)


class MCPClientManager(BaseComponentManager[IMCPClient]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_MCP_CLIENTS, IMCPClient, entry_points_loader, config_section="mcp")


class HookManager(BaseComponentManager[IHook]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_HOOKS, IHook, entry_points_loader, config_section="hooks")


class ConfigProviderManager(BaseComponentManager[IConfigProvider]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_CONFIG_PROVIDERS, IConfigProvider, entry_points_loader, config_section=None)


class PromptStoreManager(BaseComponentManager[IPromptStore]):
    def __init__(self, entry_points_loader: EntryPointLoader | None = None) -> None:
        super().__init__(ENTRYPOINT_PROMPT_STORES, IPromptStore, entry_points_loader, config_section="prompt_store")
