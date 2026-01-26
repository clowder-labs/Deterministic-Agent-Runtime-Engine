import pytest

pytest.skip(
    "Legacy ConfigManager reload flow is archived; port to canonical dare_framework once "
    "equivalent config manager support exists.",
    allow_module_level=True,
)

from dare_framework.config.manager import ConfigManager


def test_config_manager_reload_returns_new_config():
    manager = ConfigManager(system={"llm": {"model": "m1"}})

    current = manager.current
    reloaded = manager.reload()

    assert current is not reloaded
    assert reloaded.llm.model == "m1"
    assert manager.current is reloaded
