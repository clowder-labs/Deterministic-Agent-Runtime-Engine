from dare_framework.core.config import build_config_from_layers, merge_config_layers
from dare_framework.contracts import ComponentType


def test_merge_config_layers_applies_overrides():
    system = {
        "llm": {"endpoint": "https://system", "model": "system-model"},
        "allowtools": ["tool_a"],
        "components": {"tool": {"disabled": ["legacy_tool"]}},
    }
    user = {
        "llm": {"model": "user-model"},
        "components": {"tool": {"disabled": ["user_disabled"]}},
    }
    project = {
        "allowtools": ["tool_b"],
        "components": {"tool": {"new_tool": {"timeout": 5}}},
    }

    merged = merge_config_layers([system, user, project])

    assert merged["llm"]["endpoint"] == "https://system"
    assert merged["llm"]["model"] == "user-model"
    assert merged["allowtools"] == ["tool_b"]
    assert merged["components"]["tool"]["disabled"] == ["user_disabled"]
    assert merged["components"]["tool"]["new_tool"]["timeout"] == 5


def test_build_config_from_layers_parses_component_config():
    layers = [
        {
            "components": {
                "mcp": {
                    "disabled": ["legacy"],
                    "default_mcp": {"url": "http://localhost"},
                }
            }
        }
    ]

    config = build_config_from_layers(layers)

    assert config.is_component_enabled(ComponentType.MCP, "default_mcp") is True
    assert config.is_component_enabled(ComponentType.MCP, "legacy") is False
    assert config.component_config(ComponentType.MCP, "default_mcp") == {"url": "http://localhost"}
