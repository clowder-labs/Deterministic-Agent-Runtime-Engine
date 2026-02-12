from dare_framework.config.types import Config


def test_hooks_config_round_trip() -> None:
    config = Config.from_dict(
        {
            "hooks": {
                "version": 1,
                "defaults": {"timeout_ms": 200},
                "entries": [],
            }
        }
    )
    payload = config.to_dict()
    assert payload["hooks"]["version"] == 1
    assert payload["hooks"]["defaults"]["timeout_ms"] == 200
