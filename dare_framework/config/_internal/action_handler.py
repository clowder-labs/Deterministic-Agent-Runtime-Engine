"""Config-domain deterministic action handlers."""

from __future__ import annotations

import dataclasses
from typing import Any

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.types import Config
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler


class ConfigActionHandler(IActionHandler):
    """Handle deterministic config-domain actions."""

    def __init__(
        self,
        *,
        config: Config | None,
        manager: IConfigProvider | None,
    ) -> None:
        self._config = config
        self._manager = manager

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.CONFIG_GET}

    # noinspection PyMethodOverriding
    async def invoke(
        self,
        action: ResourceAction,
        **_params: Any,
    ) -> Any:
        if action == ResourceAction.CONFIG_GET:
            return self._config_get()
        raise ValueError(f"unsupported config action: {action.value}")

    def _config_get(self) -> dict[str, Any]:
        cfg = self._resolve_config()
        if dataclasses.is_dataclass(cfg):
            data = dataclasses.asdict(cfg)
        else:
            data = {"config": str(cfg)}

        return {
            "workspace_dir": data.get("workspace_dir"),
            "user_dir": data.get("user_dir"),
            "llm": data.get("llm"),
            "cli": data.get("cli"),
            "allow_tools": data.get("allow_tools"),
            "allow_mcps": data.get("allow_mcps"),
            "mcp_paths": data.get("mcp_paths"),
            "tools": data.get("tools"),
            "mcp": data.get("mcp"),
            "default_prompt_id": data.get("default_prompt_id"),
        }

    def _resolve_config(self) -> Config:
        if self._config is not None:
            return self._config
        if self._manager is not None:
            return self._manager.current()
        raise RuntimeError("config action handler requires config or config provider")


__all__ = ["ConfigActionHandler"]
