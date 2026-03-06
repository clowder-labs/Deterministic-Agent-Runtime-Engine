from __future__ import annotations

from pathlib import Path

import pytest

from client.runtime.bootstrap import (
    RuntimeOptions,
    _resolve_system_prompt_override,
    apply_runtime_overrides,
)
from dare_framework.config.types import Config
from dare_framework.model.types import Prompt


class _DummyPromptStore:
    def __init__(self, base_prompt: Prompt) -> None:
        self._base_prompt = base_prompt

    def get(self, prompt_id: str, *, model: str | None = None, version: str | None = None) -> Prompt:
        _ = (prompt_id, model, version)
        return self._base_prompt


class _MissingPromptStore:
    def get(self, prompt_id: str, *, model: str | None = None, version: str | None = None) -> Prompt:
        _ = (prompt_id, model, version)
        raise KeyError(prompt_id)


class _DummyModel:
    name = "openai"
    model = "gpt-4o-mini"


@pytest.fixture
def _base_prompt() -> Prompt:
    return Prompt(
        prompt_id="base.system",
        role="system",
        content="BASE",
        supported_models=["*"],
        order=0,
    )


def test_apply_runtime_overrides_applies_system_prompt_cli_flags(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    base = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "system_prompt": {"mode": "append", "path": ".dare/prompts/base.txt"},
        }
    )
    options = RuntimeOptions(
        workspace_dir=workspace,
        user_dir=user_dir,
        system_prompt_mode="replace",
        system_prompt_file=".dare/prompts/override.txt",
    )

    effective = apply_runtime_overrides(base, options)

    assert effective.system_prompt.mode == "replace"
    assert effective.system_prompt.content is None
    assert effective.system_prompt.path == ".dare/prompts/override.txt"


def test_apply_runtime_overrides_text_override_clears_config_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    base = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "system_prompt": {"mode": "append", "path": ".dare/prompts/base.txt"},
        }
    )
    options = RuntimeOptions(
        workspace_dir=workspace,
        user_dir=user_dir,
        system_prompt_text="INLINE",
    )

    effective = apply_runtime_overrides(base, options)

    assert effective.system_prompt.content == "INLINE"
    assert effective.system_prompt.path is None


def test_apply_runtime_overrides_text_without_mode_defaults_to_replace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    base = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "system_prompt": {"mode": "append", "path": ".dare/prompts/base.txt"},
        }
    )
    options = RuntimeOptions(
        workspace_dir=workspace,
        user_dir=user_dir,
        system_prompt_text="INLINE",
    )

    effective = apply_runtime_overrides(base, options)

    assert effective.system_prompt.content == "INLINE"
    assert effective.system_prompt.path is None
    assert effective.system_prompt.mode == "replace"


def test_resolve_system_prompt_override_replace_mode(_base_prompt: Prompt) -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "system_prompt": {"mode": "replace", "content": "ONLY"},
        }
    )

    override = _resolve_system_prompt_override(
        config=config,
        model=_DummyModel(),
        prompt_store=_DummyPromptStore(_base_prompt),
    )

    assert override is not None
    assert override.content == "ONLY"


def test_resolve_system_prompt_override_replace_mode_without_base_prompt_lookup() -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "default_prompt_id": "custom.system",
            "system_prompt": {"mode": "replace", "content": "ONLY"},
        }
    )

    override = _resolve_system_prompt_override(
        config=config,
        model=_DummyModel(),
        prompt_store=_MissingPromptStore(),
    )

    assert override is not None
    assert override.prompt_id == "custom.system"
    assert override.role == "system"
    assert override.content == "ONLY"


def test_resolve_system_prompt_override_append_mode(_base_prompt: Prompt) -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "system_prompt": {"mode": "append", "content": "EXTRA"},
        }
    )

    override = _resolve_system_prompt_override(
        config=config,
        model=_DummyModel(),
        prompt_store=_DummyPromptStore(_base_prompt),
    )

    assert override is not None
    assert override.content == "BASE\n\n---\n\nEXTRA"


def test_resolve_system_prompt_override_append_mode_requires_base_prompt() -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "system_prompt": {"mode": "append", "content": "EXTRA"},
        }
    )

    with pytest.raises(ValueError, match="Prompt not found: base.system"):
        _resolve_system_prompt_override(
            config=config,
            model=_DummyModel(),
            prompt_store=_MissingPromptStore(),
        )


def test_resolve_system_prompt_override_defaults_mode_to_replace(_base_prompt: Prompt) -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "system_prompt": {"content": "INLINE"},
        }
    )

    override = _resolve_system_prompt_override(
        config=config,
        model=_DummyModel(),
        prompt_store=_DummyPromptStore(_base_prompt),
    )

    assert override is not None
    assert override.content == "INLINE"


def test_resolve_system_prompt_override_reads_relative_file(tmp_path: Path, _base_prompt: Prompt) -> None:
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = workspace / ".dare" / "prompts"
    path.mkdir(parents=True, exist_ok=True)
    prompt_file = path / "extra.txt"
    prompt_file.write_text("FROM_FILE", encoding="utf-8")

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "system_prompt": {"mode": "append", "path": ".dare/prompts/extra.txt"},
        }
    )

    override = _resolve_system_prompt_override(
        config=config,
        model=_DummyModel(),
        prompt_store=_DummyPromptStore(_base_prompt),
    )

    assert override is not None
    assert override.content == "BASE\n\n---\n\nFROM_FILE"


def test_resolve_system_prompt_override_rejects_content_and_path(_base_prompt: Prompt) -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "system_prompt": {"mode": "replace", "content": "x", "path": "y.txt"},
        }
    )

    with pytest.raises(ValueError, match="system_prompt.content and system_prompt.path are mutually exclusive"):
        _resolve_system_prompt_override(
            config=config,
            model=_DummyModel(),
            prompt_store=_DummyPromptStore(_base_prompt),
        )
