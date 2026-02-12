"""Unit tests for dare_framework.tool gateway."""

import pytest

from dare_framework.tool._internal import EchoTool, NativeToolProvider, NoopTool
from dare_framework.tool.tool_gateway import ToolGateway
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.plan.types import Envelope


class TestToolManagerGateway:
    """Tests for ToolGateway backed by ToolManager."""

    @pytest.fixture
    def tool_manager(self):
        return ToolManager(load_entrypoints=False)

    @pytest.fixture
    def gateway(self, tool_manager):
        return ToolGateway(tool_manager)

    @pytest.fixture
    def provider_with_tools(self):
        provider = NativeToolProvider()
        provider.register_tool(NoopTool())
        provider.register_tool(EchoTool())
        return provider

    @pytest.mark.asyncio
    async def test_register_provider(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)
        capabilities = gateway.list_capabilities()
        assert len(capabilities) == 2
        names = {c.name for c in capabilities}
        assert "noop" in names
        assert "echo" in names

    @pytest.mark.asyncio
    async def test_unregister_provider(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)
        assert len(gateway.list_capabilities()) == 2

        result = tool_manager.unregister_provider(provider_with_tools)
        assert result is True
        assert len(gateway.list_capabilities()) == 0

    @pytest.mark.asyncio
    async def test_unregister_unknown_provider(self, tool_manager, provider_with_tools):
        result = tool_manager.unregister_provider(provider_with_tools)
        assert result is False

    @pytest.mark.asyncio
    async def test_invoke_noop(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)
        caps = gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope(allowed_capability_ids=[cap_ids["noop"], cap_ids["echo"]])
        result = await gateway.invoke(cap_ids["noop"], envelope=envelope)

        assert result.success is True
        assert result.output["status"] == "noop completed"

    @pytest.mark.asyncio
    async def test_invoke_echo(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)
        caps = gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope(allowed_capability_ids=[cap_ids["noop"], cap_ids["echo"]])
        result = await gateway.invoke(cap_ids["echo"], envelope=envelope, message="hello")

        assert result.success is True
        assert result.output["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_invoke_not_allowed_by_envelope(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)
        caps = gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope(allowed_capability_ids=[cap_ids["noop"]])
        with pytest.raises(PermissionError) as exc_info:
            await gateway.invoke(cap_ids["echo"], envelope=envelope, message="hello")

        assert "not allowed by envelope" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_unknown_capability(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)

        envelope = Envelope()
        with pytest.raises(KeyError) as exc_info:
            await gateway.invoke("unknown", envelope=envelope)

        assert "Unknown capability id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_envelope_allows_all(self, tool_manager, gateway, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)
        caps = gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope()
        result = await gateway.invoke(cap_ids["echo"], envelope=envelope, message="test")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_health_check(self, tool_manager, provider_with_tools):
        tool_manager.register_provider(provider_with_tools)

        health = await tool_manager.health_check()

        assert "tool_manager" in health
        assert "provider_0" in health
