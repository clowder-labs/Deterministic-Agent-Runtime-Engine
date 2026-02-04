"""Unit tests for dare_framework.tool gateway."""

import pytest

from dare_framework.tool._internal import EchoTool, NativeToolProvider, NoopTool
from dare_framework.tool.default_tool_manager import ToolManager
from dare_framework.plan.types import Envelope


class TestToolManagerGateway:
    """Tests for ToolManager as the default gateway."""

    @pytest.fixture
    def gateway(self):
        return ToolManager()

    @pytest.fixture
    def provider_with_tools(self):
        provider = NativeToolProvider()
        provider.register_tool(NoopTool())
        provider.register_tool(EchoTool())
        return provider

    @pytest.mark.asyncio
    async def test_register_provider(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        capabilities = await gateway.list_capabilities()
        assert len(capabilities) == 2
        names = {c.name for c in capabilities}
        assert "noop" in names
        assert "echo" in names

    @pytest.mark.asyncio
    async def test_unregister_provider(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        assert len(await gateway.list_capabilities()) == 2

        result = gateway.unregister_provider(provider_with_tools)
        assert result is True
        assert len(await gateway.list_capabilities()) == 0

    @pytest.mark.asyncio
    async def test_unregister_unknown_provider(self, gateway, provider_with_tools):
        result = gateway.unregister_provider(provider_with_tools)
        assert result is False

    @pytest.mark.asyncio
    async def test_invoke_noop(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        caps = await gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope(allowed_capability_ids=[cap_ids["noop"], cap_ids["echo"]])
        result = await gateway.invoke(cap_ids["noop"], {}, envelope=envelope)

        assert result.success is True
        assert result.output["status"] == "noop completed"

    @pytest.mark.asyncio
    async def test_invoke_echo(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        caps = await gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope(allowed_capability_ids=[cap_ids["noop"], cap_ids["echo"]])
        result = await gateway.invoke(cap_ids["echo"], {"message": "hello"}, envelope=envelope)

        assert result.success is True
        assert result.output["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_invoke_not_allowed_by_envelope(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        caps = await gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope(allowed_capability_ids=[cap_ids["noop"]])
        with pytest.raises(PermissionError) as exc_info:
            await gateway.invoke(cap_ids["echo"], {"message": "hello"}, envelope=envelope)

        assert "not allowed by envelope" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_unknown_capability(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)

        envelope = Envelope()
        with pytest.raises(KeyError) as exc_info:
            await gateway.invoke("unknown", {}, envelope=envelope)

        assert "Unknown capability id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_envelope_allows_all(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        caps = await gateway.list_capabilities()
        cap_ids = {cap.name: cap.id for cap in caps}

        envelope = Envelope()
        result = await gateway.invoke(cap_ids["echo"], {"message": "test"}, envelope=envelope)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_health_check(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)

        health = await gateway.health_check()

        assert "tool_manager" in health
        assert "provider_0" in health
