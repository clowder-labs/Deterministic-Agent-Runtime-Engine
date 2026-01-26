"""Unit tests for dare_framework.tool NativeToolProvider."""

import pytest

from dare_framework.tool import (
    NativeToolProvider,
    NoopTool,
    EchoTool,
    CapabilityType,
    CapabilityKind,
    ProviderStatus,
    RunContext,
)


class TestNativeToolProvider:
    """Tests for NativeToolProvider."""

    @pytest.fixture
    def provider(self):
        return NativeToolProvider()

    @pytest.fixture
    def noop_tool(self):
        return NoopTool()

    @pytest.fixture
    def echo_tool(self):
        return EchoTool()

    def test_register_tool(self, provider, noop_tool):
        provider.register_tool(noop_tool)
        assert provider.get_tool("noop") is noop_tool

    def test_register_duplicate_raises(self, provider, noop_tool):
        provider.register_tool(noop_tool)
        
        with pytest.raises(ValueError) as exc_info:
            provider.register_tool(noop_tool)
        
        assert "already registered" in str(exc_info.value)

    def test_unregister_tool(self, provider, noop_tool):
        provider.register_tool(noop_tool)
        result = provider.unregister_tool("noop")
        
        assert result is True
        assert provider.get_tool("noop") is None

    def test_unregister_unknown_tool(self, provider):
        result = provider.unregister_tool("unknown")
        assert result is False

    def test_get_tool_unknown(self, provider):
        assert provider.get_tool("unknown") is None

    @pytest.mark.asyncio
    async def test_list_capabilities(self, provider, noop_tool, echo_tool):
        provider.register_tool(noop_tool)
        provider.register_tool(echo_tool)
        
        capabilities = await provider.list()
        
        assert len(capabilities) == 2
        cap_dict = {c.id: c for c in capabilities}
        
        # Check noop capability
        noop_cap = cap_dict["noop"]
        assert noop_cap.type == CapabilityType.TOOL
        assert noop_cap.name == "noop"
        assert noop_cap.metadata is not None
        assert noop_cap.metadata["risk_level"] == "read_only"
        assert noop_cap.metadata["requires_approval"] is False
        assert noop_cap.metadata["capability_kind"] == CapabilityKind.TOOL
        
        # Check echo capability
        echo_cap = cap_dict["echo"]
        assert echo_cap.description == "Echoes back the input message."

    @pytest.mark.asyncio
    async def test_invoke_noop(self, provider, noop_tool):
        provider.register_tool(noop_tool)
        
        result = await provider.invoke("noop", {})
        
        assert result.success is True
        assert result.output["status"] == "noop completed"

    @pytest.mark.asyncio
    async def test_invoke_echo(self, provider, echo_tool):
        provider.register_tool(echo_tool)
        
        result = await provider.invoke("echo", {"message": "hello world"})
        
        assert result.success is True
        assert result.output["echo"] == "hello world"

    @pytest.mark.asyncio
    async def test_invoke_unknown_raises(self, provider):
        with pytest.raises(KeyError) as exc_info:
            await provider.invoke("unknown", {})
        
        assert "Tool not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, provider, noop_tool):
        provider.register_tool(noop_tool)
        status = await provider.health_check()
        assert status == ProviderStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_empty(self, provider):
        status = await provider.health_check()
        assert status == ProviderStatus.DEGRADED

    def test_list_tools_for_llm(self, provider, noop_tool, echo_tool):
        provider.register_tool(noop_tool)
        provider.register_tool(echo_tool)
        
        tool_defs = provider.list_tools()
        
        assert len(tool_defs) == 2
        
        # Check structure
        for tool_def in tool_defs:
            assert tool_def["type"] == "function"
            assert "function" in tool_def
            assert "name" in tool_def["function"]
            assert "description" in tool_def["function"]
            assert "parameters" in tool_def["function"]

    def test_set_run_context(self, provider, noop_tool):
        custom_context = RunContext(deps={"key": "value"}, metadata={"trace": True})
        provider.set_run_context(custom_context)
        provider.register_tool(noop_tool)
        
        assert provider._run_context == custom_context
