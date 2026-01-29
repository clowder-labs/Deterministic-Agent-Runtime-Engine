"""Unit tests for dare_framework.tool NativeToolProvider."""

import pytest

from dare_framework.tool import NativeToolProvider, NoopTool, EchoTool


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

    def test_list_tools(self, provider, noop_tool, echo_tool):
        provider.register_tool(noop_tool)
        provider.register_tool(echo_tool)

        tools = provider.list_tools()

        assert [tool.name for tool in tools] == ["noop", "echo"]
