from __future__ import annotations

from dare_framework.builder.plugin_system.component import IComponentRegistrar
from dare_framework.contracts import ComponentType


class BaseComponent:
    order = 100

    @property
    def component_name(self) -> str:
        name = getattr(self, "name", None)
        if isinstance(name, str):
            return name
        return self.__class__.__name__

    async def init(
        self,
        config: object | None = None,
        prompts: object | None = None,
    ) -> None:
        return None

    def register(self, registrar: IComponentRegistrar) -> None:
        registrar.register_component(self)

    async def close(self) -> None:
        return None


class ConfigurableComponent(BaseComponent):
    component_type: ComponentType | None = None

    @property
    def component_type(self) -> ComponentType:
        if self.__class__.component_type is None:
            raise ValueError("component_type must be set for configurable components")
        return self.__class__.component_type
