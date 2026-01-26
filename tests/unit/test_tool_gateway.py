"""Unit tests for dare_framework.tool gateway."""

import asyncio

import pytest

from dare_framework.tool import (
    DefaultToolGateway,
    NativeToolProvider,
    NoopTool,
    EchoTool,
    CapabilityDescriptor,
    CapabilityType,
    ProviderStatus,
)
from dare_framework.plan.types import Envelope


class TestDefaultToolGateway:
    """Tests for DefaultToolGateway."""

    @pytest.fixture
    def gateway(self):
        return DefaultToolGateway()

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
    async def test_register_invalid_provider_raises(self, gateway):
        with pytest.raises(TypeError):
            gateway.register_provider("not a provider")

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
        await gateway.list_capabilities()
        
        envelope = Envelope(allowed_capability_ids=["noop", "echo"])
        result = await gateway.invoke("noop", {}, envelope=envelope)
        
        assert result.success is True
        assert result.output["status"] == "noop completed"

    @pytest.mark.asyncio
    async def test_invoke_echo(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        await gateway.list_capabilities()
        
        envelope = Envelope(allowed_capability_ids=["noop", "echo"])
        result = await gateway.invoke("echo", {"message": "hello"}, envelope=envelope)
        
        assert result.success is True
        assert result.output["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_invoke_not_allowed_by_envelope(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        await gateway.list_capabilities()
        
        envelope = Envelope(allowed_capability_ids=["noop"])  # echo not allowed
        
        with pytest.raises(PermissionError) as exc_info:
            await gateway.invoke("echo", {"message": "hello"}, envelope=envelope)
        
        assert "not allowed by envelope" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_unknown_capability(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        await gateway.list_capabilities()
        
        envelope = Envelope()  # empty allow-list means all allowed
        
        with pytest.raises(KeyError) as exc_info:
            await gateway.invoke("unknown", {}, envelope=envelope)
        
        assert "Unknown capability id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_envelope_allows_all(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        await gateway.list_capabilities()
        
        envelope = Envelope()  # empty allowed_capability_ids
        result = await gateway.invoke("echo", {"message": "test"}, envelope=envelope)
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_capability_caching(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        
        # First call
        caps1 = await gateway.list_capabilities()
        # Second call should use cache
        caps2 = await gateway.list_capabilities()
        
        assert caps1 == caps2

    def test_invalidate_cache(self, gateway):
        gateway._cache_timestamp = 100.0
        gateway.invalidate_cache()
        assert gateway._cache_timestamp == 0.0

    @pytest.mark.asyncio
    async def test_health_check(self, gateway, provider_with_tools):
        gateway.register_provider(provider_with_tools)
        
        health = await gateway.health_check()
        
        assert "provider_0" in health
        assert health["provider_0"] == ProviderStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_duplicate_capability_id_raises(self, gateway):
        provider1 = NativeToolProvider()
        provider1.register_tool(NoopTool())
        
        provider2 = NativeToolProvider()
        provider2.register_tool(NoopTool())  # Same tool name
        
        gateway.register_provider(provider1)
        gateway.register_provider(provider2)
        
        with pytest.raises(ValueError) as exc_info:
            await gateway.list_capabilities()
        
        assert "Duplicate capability id" in str(exc_info.value)
