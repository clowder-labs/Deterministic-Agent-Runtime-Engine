from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from dare_framework.config.types import Config
from dare_framework.mcp.manager import MCPManager


@dataclass
class _ServerConfig:
    name: str
    enabled: bool = True


class _FakeProvider:
    def __init__(self, clients: list[Any]) -> None:
        self.clients = list(clients)
        self.initialized = False
        self.closed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.closed = True

    def list_tools(self) -> list[Any]:
        return []


class _FakeToolManager:
    def __init__(self, *, fail_register_once: bool = False, tool_defs: list[dict[str, Any]] | None = None) -> None:
        self.fail_register_once = fail_register_once
        self.tool_defs = list(tool_defs or [])
        self.providers: list[Any] = []
        self.unregistered: list[Any] = []
        self.refresh_calls = 0

    def register_provider(self, provider: Any) -> None:
        if self.fail_register_once:
            self.fail_register_once = False
            raise RuntimeError("register failed")
        self.providers.append(provider)

    def unregister_provider(self, provider: Any) -> bool:
        self.unregistered.append(provider)
        if provider in self.providers:
            self.providers.remove(provider)
            return True
        return False

    async def refresh(self) -> list[Any]:
        self.refresh_calls += 1
        return []

    def list_tool_defs(self) -> list[dict[str, Any]]:
        return list(self.tool_defs)


def test_mcp_manager_requires_non_null_config() -> None:
    with pytest.raises(ValueError, match="non-null Config"):
        MCPManager(None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_mcp_manager_load_provider_filters_allowmcps() -> None:
    captured: dict[str, Any] = {}
    providers: list[_FakeProvider] = []

    def _load_configs(
        paths: list[str] | None,
        *,
        workspace_dir: str | None = None,
        user_dir: str | None = None,
    ) -> list[_ServerConfig]:
        captured["paths"] = paths
        captured["workspace_dir"] = workspace_dir
        captured["user_dir"] = user_dir
        return [_ServerConfig(name="allowed"), _ServerConfig(name="blocked")]

    async def _create_clients(
        configs: list[_ServerConfig],
        *,
        connect: bool = False,
        skip_errors: bool = True,
    ) -> list[str]:
        captured["client_configs"] = [item.name for item in configs]
        captured["connect"] = connect
        captured["skip_errors"] = skip_errors
        return [item.name for item in configs]

    def _provider_factory(clients: list[str]) -> _FakeProvider:
        provider = _FakeProvider(clients)
        providers.append(provider)
        return provider

    manager = MCPManager(
        Config(workspace_dir="/workspace", user_dir="/user", allow_mcps=["allowed"]),
        load_configs=_load_configs,
        create_clients=_create_clients,
        provider_factory=_provider_factory,
    )

    provider = await manager.load_provider(paths=["/workspace/.dare/mcp"])

    assert captured["paths"] == ["/workspace/.dare/mcp"]
    assert captured["workspace_dir"] == "/workspace"
    assert captured["user_dir"] == "/user"
    assert captured["client_configs"] == ["allowed"]
    assert captured["connect"] is True
    assert captured["skip_errors"] is True
    assert provider is providers[0]
    assert provider.initialized is True


@pytest.mark.asyncio
async def test_mcp_manager_reload_replaces_provider_and_closes_old() -> None:
    old_provider = _FakeProvider([])
    new_provider = _FakeProvider([])
    gateway = _FakeToolManager()
    gateway.providers.append(old_provider)
    manager = MCPManager(Config(), provider=old_provider)

    async def _load_provider(*, paths: list[str] | None = None) -> _FakeProvider:
        assert paths is None
        return new_provider

    manager.load_provider = _load_provider  # type: ignore[assignment]
    result = await manager.reload(gateway)

    assert result is new_provider
    assert manager.provider is new_provider
    assert old_provider.closed is True
    assert gateway.unregistered == [old_provider]
    assert gateway.providers == [new_provider]
    assert gateway.refresh_calls == 1


@pytest.mark.asyncio
async def test_mcp_manager_reload_rolls_back_when_register_fails() -> None:
    old_provider = _FakeProvider([])
    new_provider = _FakeProvider([])
    gateway = _FakeToolManager(fail_register_once=True)
    gateway.providers.append(old_provider)
    manager = MCPManager(Config(), provider=old_provider)

    async def _load_provider(*, paths: list[str] | None = None) -> _FakeProvider:
        assert paths is None
        return new_provider

    manager.load_provider = _load_provider  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="register failed"):
        await manager.reload(gateway)

    assert manager.provider is old_provider
    assert new_provider.closed is True
    assert old_provider.closed is False
    assert gateway.providers == [old_provider]
    assert gateway.refresh_calls == 1


@pytest.mark.asyncio
async def test_mcp_manager_unload_unregisters_and_closes_provider() -> None:
    provider = _FakeProvider([])
    gateway = _FakeToolManager()
    gateway.providers.append(provider)
    manager = MCPManager(Config(), provider=provider)

    removed = await manager.unload(gateway)

    assert removed is True
    assert manager.provider is None
    assert provider.closed is True
    assert gateway.providers == []
    assert gateway.refresh_calls == 1


def test_mcp_manager_list_mcp_tool_defs_filters_non_mcp_tools() -> None:
    gateway = _FakeToolManager(
        tool_defs=[
            {"function": {"name": "read_file"}},
            {"function": {"name": "math:add"}},
            {"function": {"name": "math:subtract"}},
            {"function": {"name": 123}},
            {"function": "invalid"},
        ]
    )
    manager = MCPManager(Config())

    all_mcp = manager.list_mcp_tool_defs(gateway)
    selected = manager.list_mcp_tool_defs(gateway, tool_name="math:add")

    assert [tool["function"]["name"] for tool in all_mcp] == ["math:add", "math:subtract"]
    assert [tool["function"]["name"] for tool in selected] == ["math:add"]
