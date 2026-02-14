from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_example_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[2]
    module_path = root / relative_path
    example_dir = module_path.parent
    if str(example_dir) not in sys.path:
        sys.path.insert(0, str(example_dir))
    # Example directories contain "-" so we load modules by file path.
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeStdioClientChannel:
    def __init__(self) -> None:
        self._sender = None

    def attach_agent_envelope_sender(self, sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self):
        async def _recv(_msg) -> None:
            return

        return _recv

    async def start(self) -> None:
        return


class _FakeAgent:
    async def start(self) -> None:
        return

    async def stop(self) -> None:
        return


class _FakeBuilder:
    last_channel = None

    def with_model(self, _model):
        return self

    def with_config(self, _config):
        return self

    def add_tools(self, *_tools):
        return self

    def with_agent_channel(self, channel):
        type(self).last_channel = channel
        return self

    async def build(self):
        return _FakeAgent()


class _FakeBaseAgent:
    @staticmethod
    def react_agent_builder(_name: str) -> _FakeBuilder:
        return _FakeBuilder()


@pytest.mark.asyncio
async def test_examples_02_with_tools_main_builds_channel(monkeypatch) -> None:
    module = _load_example_module(
        "examples_02_with_tools_main",
        "examples/02-with-tools/main.py",
    )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(module, "OpenRouterModelAdapter", lambda **_kwargs: object())
    monkeypatch.setattr(module, "BaseAgent", _FakeBaseAgent)
    monkeypatch.setattr(module, "StdioClientChannel", _FakeStdioClientChannel)

    await module.main()
    assert _FakeBuilder.last_channel is not None
