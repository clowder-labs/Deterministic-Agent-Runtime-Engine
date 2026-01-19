from dare_framework2.config import ConfigManager


def test_config_manager_merge_precedence():
    manager = ConfigManager(
        system={"llm": {"model": "sys", "temperature": 0.1}},
        project={"llm": {"model": "project"}},
        user={"llm": {"model": "user"}},
        session={"llm": {"model": "session"}, "runtime": {"timeout": 10}},
    )

    assert manager.current.llm.model == "session"
    assert manager.get("llm.temperature") == 0.1
    assert manager.get_namespace("runtime") == {"timeout": 10}


def test_config_manager_reload_returns_new_config():
    manager = ConfigManager(system={"llm": {"model": "m1"}})

    current = manager.current
    reloaded = manager.reload()

    assert current is not reloaded
    assert reloaded.llm.model == "m1"
    assert manager.current is reloaded


def test_config_manager_hash_is_stable():
    manager = ConfigManager(system={"llm": {"model": "m1"}}, project={"tools": {"noop": {}}})

    first_hash = manager.config_hash
    manager.reload()
    assert manager.config_hash == first_hash


def test_config_manager_get_default():
    manager = ConfigManager()

    assert manager.get("missing.path", default=123) == 123
    assert manager.get_namespace("missing") == {}
