from dare_framework.components.config_provider import LayeredConfigProvider


def test_layered_config_merge_precedence():
    provider = LayeredConfigProvider(
        system={"llm": {"model": "sys", "temperature": 0.1}},
        project={"llm": {"model": "project"}},
        user={"llm": {"model": "user"}},
        session={"runtime": {"timeout": 10}},
    )

    assert provider.get("llm.model") == "user"
    assert provider.get("llm.temperature") == 0.1
    assert provider.get_namespace("runtime") == {"timeout": 10}
    assert provider.config_hash
    assert "session" in provider.sources
