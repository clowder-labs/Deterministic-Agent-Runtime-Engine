from __future__ import annotations

import importlib
from dataclasses import dataclass


def test_checkpoint_defaults_module_exports_are_importable() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")

    for symbol in (
        "MemoryCheckpointStore",
        "DefaultCheckpointSaveRestore",
        "StmContributor",
        "WorkspaceGitContributor",
        "SessionStateContributor",
        "SessionContextContributor",
    ):
        assert hasattr(defaults, symbol), f"missing checkpoint default symbol: {symbol}"


@dataclass
class _DummyConfig:
    model: str


@dataclass
class _DummySessionContext:
    session_id: str
    task_id: str
    config: _DummyConfig | None


@dataclass
class _DummyCtx:
    session_context: _DummySessionContext | None


def test_session_context_contributor_preserves_serialized_config_dict() -> None:
    defaults = importlib.import_module("dare_framework.checkpoint.defaults")
    contributor = defaults.SessionContextContributor()
    ctx = _DummyCtx(
        session_context=_DummySessionContext(
            session_id="s-1",
            task_id="t-1",
            config=_DummyConfig(model="gpt-4.1"),
        )
    )

    payload = contributor.serialize(ctx)

    assert payload is not None
    assert payload["config"] == {"model": "gpt-4.1"}
