import json
from pathlib import Path

import pytest

from dare_framework.config import FileConfigProvider, build_config_provider
from dare_framework.infra.component import ComponentType


def _write_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_file_config_provider_merges_user_and_workspace(tmp_path: Path) -> None:
    user_dir = tmp_path / "user"
    workspace_dir = tmp_path / "workspace"
    user_dir.mkdir()
    workspace_dir.mkdir()

    _write_config(
        user_dir / ".dare" / "config.json",
        {
            "llm": {"model": "user-model", "proxy": {"use_system_proxy": True}},
            "allowtools": ["tool_a"],
            "allowmcps": ["user_mcp"],
            "mcp": {"user": {"endpoint": "http://user-mcp"}},
            "components": {"validator": {"disabled": ["legacy_validator"]}},
        },
    )
    _write_config(
        workspace_dir / ".dare" / "config.json",
        {
            "llm": {
                "model": "workspace-model",
                "proxy": {"disabled": True, "http": "http://proxy:8080"},
            },
            "allowmcps": ["workspace_mcp"],
            "tools": {"local_command": {"timeout": 12}},
            "components": {"hook": {"stdout": {"level": "info"}}},
        },
    )

    provider = FileConfigProvider(workspace_dir=workspace_dir, user_dir=user_dir)
    config = provider.current()

    class DummyValidator:
        def __init__(self, name: str) -> None:
            self.name = name

        @property
        def component_type(self) -> ComponentType:
            return ComponentType.VALIDATOR

    class DummyHook:
        def __init__(self, name: str) -> None:
            self.name = name

        @property
        def component_type(self) -> ComponentType:
            return ComponentType.HOOK

    assert config.llm.model == "workspace-model"
    assert config.llm.proxy.disabled is True
    assert config.llm.proxy.use_system_proxy is False
    assert config.llm.proxy.http is None
    assert config.allowtools == ["tool_a"]
    assert config.allowmcps == ["workspace_mcp"]
    assert config.mcp["user"]["endpoint"] == "http://user-mcp"
    assert config.tools["local_command"]["timeout"] == 12
    assert config.is_component_enabled(DummyValidator("legacy_validator")) is False
    assert config.component_config(DummyHook("stdout")) == {"level": "info"}
    assert config.workspace_dir == str(workspace_dir)
    assert config.user_dir == str(user_dir)


def test_file_config_provider_defaults_when_missing_files(tmp_path: Path) -> None:
    user_dir = tmp_path / "user"
    workspace_dir = tmp_path / "workspace"
    user_dir.mkdir()
    workspace_dir.mkdir()

    provider = FileConfigProvider(workspace_dir=workspace_dir, user_dir=user_dir)
    config = provider.current()

    assert config.workspace_dir == str(workspace_dir)
    assert config.user_dir == str(user_dir)
    assert (workspace_dir / ".dare" / "config.json").exists()
    assert (user_dir / ".dare" / "config.json").exists()


def test_build_config_provider_returns_file_provider(tmp_path: Path) -> None:
    provider = build_config_provider(
        workspace_dir=tmp_path / "workspace",
        user_dir=tmp_path / "user",
    )

    assert isinstance(provider, FileConfigProvider)
    assert provider.filename == ".dare/config.json"


def test_file_config_provider_loads_fixture_files() -> None:
    base_dir = Path(__file__).resolve().parent / "fixtures" / "config_provider"
    user_dir = base_dir / "user"
    workspace_dir = base_dir / "workspace"

    provider = FileConfigProvider(workspace_dir=workspace_dir, user_dir=user_dir)
    config = provider.current()

    assert config.llm.model == "workspace-fixture-model"
    assert config.allowtools == ["fixture_tool"]
    assert config.allowmcps == ["fixture_mcp_workspace"]
    assert config.mcp["fixture_user"]["endpoint"] == "http://fixture-user-mcp"
    assert config.tools["fixture_tool"]["timeout"] == 9
    class DummyHook:
        def __init__(self, name: str) -> None:
            self.name = name

        @property
        def component_type(self) -> ComponentType:
            return ComponentType.HOOK

    assert config.component_config(DummyHook("stdout")) == {"level": "debug"}


def test_file_config_provider_prefers_project_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / "subdir").mkdir()
    user_dir = tmp_path / "user"
    user_dir.mkdir()

    monkeypatch.chdir(repo_root / "subdir")

    provider = FileConfigProvider(user_dir=user_dir)
    config = provider.current()

    assert config.workspace_dir == str(repo_root)
    assert config.user_dir == str(user_dir)
    assert (repo_root / ".dare" / "config.json").exists()
