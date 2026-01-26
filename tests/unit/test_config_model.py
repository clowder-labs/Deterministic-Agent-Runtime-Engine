from dataclasses import FrozenInstanceError

import pytest

from dare_framework.config.types import ComponentType, Config, ConfigSnapshot


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

    assert config.is_component_enabled(ComponentType.VALIDATOR, "default") is True
    assert config.is_component_enabled("validator", "legacy_validator") is False
    assert config.component_config(ComponentType.VALIDATOR, "default") == {"mode": "strict"}


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
            "allowtools": ["tool_a"],
            "components": {"hook": {"stdout": {"level": "info"}}},
        }
    )

    payload = config.to_dict()

    assert payload["llm"]["adapter"] == "openai"
    assert payload["llm"]["model"] == "gpt-4o"
    assert payload["llm"]["extra_field"] == 1
    assert payload["allowtools"] == ["tool_a"]
    assert payload["components"]["hook"]["stdout"] == {"level": "info"}


def test_config_snapshot_is_immutable() -> None:
    snapshot = ConfigSnapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.config = Config()
