from dataclasses import FrozenInstanceError

import pytest

from dare_framework.config.types import Config
from dare_framework.infra.component import ComponentType


def test_proxy_disabled_overrides_other_fields() -> None:
    config = Config.from_dict(
        {
            "llm": {
                "proxy": {
                    "disabled": True,
                    "http": "http://proxy:8080",
                    "use_system_proxy": True,
                }
            }
        }
    )

    proxy = config.llm.proxy
    assert proxy.disabled is True
    assert proxy.use_system_proxy is False
    assert proxy.http is None
    assert proxy.https is None
    assert proxy.no_proxy is None


def test_system_proxy_excludes_explicit_proxy() -> None:
    config = Config.from_dict(
        {"llm": {"proxy": {"use_system_proxy": True, "https": "https://proxy:8443"}}}
    )

    proxy = config.llm.proxy
    assert proxy.use_system_proxy is True
    assert proxy.https is None
    assert proxy.http is None


def test_proxy_is_enabled_for_explicit_values() -> None:
    config = Config.from_dict({"llm": {"proxy": {"http": "http://proxy:8080"}}})

    proxy = config.llm.proxy
    assert proxy.is_enabled() is True


def test_component_enablement_and_config_lookup() -> None:
    config = Config.from_dict(
        {
            "components": {
                "validator": {
                    "disabled": ["legacy_validator"],
                    "default": {"mode": "strict"},
                }
            }
        }
    )

    class DummyValidator:
        def __init__(self, name: str) -> None:
            self.name = name

        @property
        def component_type(self) -> ComponentType:
            return ComponentType.VALIDATOR

    assert config.is_component_enabled(DummyValidator("default")) is True
    assert config.is_component_enabled(DummyValidator("legacy_validator")) is False
    assert config.component_config(DummyValidator("default")) == {"mode": "strict"}


def test_config_from_dict_supports_workspace_roots_and_user_dir() -> None:
    config = Config.from_dict(
        {
            "workspace_roots": ["/tmp/workspace"],
            "user_dir": "/tmp/user",
        }
    )

    assert config.workspace_dir == "/tmp/workspace"
    assert config.user_dir == "/tmp/user"


def test_config_to_dict_round_trip() -> None:
    config = Config.from_dict(
        {
            "llm": {"adapter": "openai", "model": "gpt-4o", "extra_field": 1},
            "cli": {"log_path": "/tmp/dare.log"},
            "allow_tools": ["tool_a"],
            "components": {"hook": {"stdout": {"level": "info"}}},
            "security": {"boundary": "noop"},
            "system_prompt": {"mode": "append", "path": ".dare/prompts/extra.txt"},
        }
    )

    payload = config.to_dict()

    assert payload["llm"]["adapter"] == "openai"
    assert payload["llm"]["model"] == "gpt-4o"
    assert payload["llm"]["extra_field"] == 1
    assert payload["cli"]["log_path"] == "/tmp/dare.log"
    assert payload["allow_tools"] == ["tool_a"]
    assert payload["components"]["hook"]["stdout"] == {"level": "info"}
    assert payload["security"]["boundary"] == "noop"
    assert payload["system_prompt"]["mode"] == "append"
    assert payload["system_prompt"]["path"] == ".dare/prompts/extra.txt"


def test_system_prompt_config_defaults_to_none_mode() -> None:
    config = Config.from_dict({"system_prompt": {"content": "always be precise"}})

    assert config.system_prompt.mode is None
    assert config.system_prompt.content == "always be precise"
    assert config.system_prompt.path is None


def test_system_prompt_config_invalid_mode_is_ignored() -> None:
    with pytest.raises(ValueError, match="invalid system_prompt.mode"):
        Config.from_dict({"system_prompt": {"mode": "invalid", "content": "x"}})


def test_config_is_immutable() -> None:
    config = Config()

    with pytest.raises(FrozenInstanceError):
        config.workspace_dir = "/tmp"
