from __future__ import annotations

from ..core.interfaces import IComponentRegistrar, IConfigProvider, IPromptStore


class BaseComponent:
    order = 100

    async def init(
        self,
        config: IConfigProvider | None = None,
        prompts: IPromptStore | None = None,
    ) -> None:
        return None

    def register(self, registrar: IComponentRegistrar) -> None:
        registrar.register_component(self)

    async def close(self) -> None:
        return None
