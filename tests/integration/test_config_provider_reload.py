from dare_framework.core.config.manager import ConfigManager


def test_config_manager_reload_returns_new_config():
    manager = ConfigManager(system={"llm": {"model": "m1"}})

    current = manager.current
    reloaded = manager.reload()

    assert current is not reloaded
    assert reloaded.llm.model == "m1"
    assert manager.current is reloaded
