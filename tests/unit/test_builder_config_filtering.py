from typing import Any

from dare_framework.builder import AgentBuilder
from dare_framework.contracts import ComponentType
from dare_framework.components.tools.noop import NoOpTool
from dare_framework.core.config import ComponentConfig
from dare_framework.core.config import Config


class NamedNoOpTool(NoOpTool):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


def test_builder_filters_disabled_tools():
    # Setup tools: one enabled, one disabled
    tool1 = NamedNoOpTool("enabled_tool")
    tool2 = NamedNoOpTool("disabled_tool")

    # Setup config
    config = Config(
        components={
            ComponentType.TOOL.value: ComponentConfig(disabled=["disabled_tool"])
        }
    )

    # Build agent
    builder = AgentBuilder("test-agent")
    builder.with_tools(tool1, tool2)
    builder.with_plugin_managers(None, config=config)
    
    # We can't easily inspect the built agent's tools without making them public,
    # but we can check if they are registered into the gateway.
    # In this MVP, we'll just check if the logic in build() executes without error.
    # For a real test, we might check the tool_gateway of the built agent.
    agent = builder.build()
    
    # Access private tool gateway via __dict__ or similar if needed for assertion
    # orchestrator = agent._orchestrator
    # gateway = orchestrator._tool_gateway
    # caps = asyncio.run(gateway.list_capabilities())
    # ...
    
    # Actually, let's just assert that only one tool (plus noop) would be in the list.
    # Since builder._tools is modified in-place, we can check it after build().
    assert any(t.name == "enabled_tool" for t in builder._tools)
    assert not any(t.name == "disabled_tool" for t in builder._tools)
    assert any(t.name == "noop" for t in builder._tools)
