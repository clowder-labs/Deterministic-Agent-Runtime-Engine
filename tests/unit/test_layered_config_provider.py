import pytest

pytest.skip(
    "Legacy ConfigManager is archived; port to canonical dare_framework once "
    "equivalent config manager support exists.",
    allow_module_level=True,
)

from dare_framework.config.manager import ConfigManager


def test_layered_config_merge_precedence():
    manager = ConfigManager(
        system={"llm": {"model": "sys", "temperature": 0.1}},
        project={"llm": {"model": "project"}},
        user={"llm": {"model": "user"}},
        session={"runtime": {"timeout": 10}},
    )

    assert manager.get("llm.model") == "user"
    assert manager.get("llm.temperature") == 0.1
    assert manager.get_namespace("runtime") == {"timeout": 10}
    assert manager.config_hash
    assert "session" in manager.sources
