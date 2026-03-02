from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.event import SQLiteEventLog
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.observability._internal.event_trace_bridge import TraceAwareEventLog
from dare_framework.security.impl import NoOpSecurityBoundary, PolicySecurityBoundary
from dare_framework.tool.types import ToolResult


class _Model:
    name = "mock-model"

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(content="ok", tool_calls=[])


class _ToolGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=True, output={})


def test_dare_builder_defaults_to_policy_security_boundary() -> None:
    builder = BaseAgent.dare_agent_builder("security-default").with_model(_Model())
    config = Config()
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._security_boundary, PolicySecurityBoundary)


def test_dare_builder_supports_noop_boundary_from_config() -> None:
    builder = BaseAgent.dare_agent_builder("security-noop").with_model(_Model())
    config = Config.from_dict({"security": {"boundary": "noop"}})
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._security_boundary, NoOpSecurityBoundary)


def test_dare_builder_treats_null_boundary_as_default_policy_boundary() -> None:
    builder = BaseAgent.dare_agent_builder("security-null").with_model(_Model())
    config = Config.from_dict({"security": {"boundary": None}})
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._security_boundary, PolicySecurityBoundary)


def test_dare_builder_explicit_security_boundary_overrides_config() -> None:
    explicit = NoOpSecurityBoundary()
    builder = BaseAgent.dare_agent_builder("security-explicit").with_model(_Model())
    builder = builder.with_security_boundary(explicit)
    config = Config.from_dict({"security": {"boundary": "policy"}})
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert agent._security_boundary is explicit


def test_dare_builder_autowires_default_event_log_when_enabled(tmp_path) -> None:
    db_path = tmp_path / ".dare" / "events.db"
    builder = BaseAgent.dare_agent_builder("event-default").with_model(_Model())
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "event_log": {"enabled": True, "path": str(db_path)},
        }
    )
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._event_log, TraceAwareEventLog)
    assert isinstance(agent._event_log._inner, SQLiteEventLog)
    assert agent._event_log._inner._path == db_path


def test_dare_builder_autowires_default_event_log_path_when_missing(tmp_path) -> None:
    expected_path = tmp_path / ".dare" / "events.db"
    builder = BaseAgent.dare_agent_builder("event-default-path").with_model(_Model())
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "event_log": {"enabled": True},
        }
    )
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._event_log, TraceAwareEventLog)
    assert isinstance(agent._event_log._inner, SQLiteEventLog)
    assert agent._event_log._inner._path == expected_path


def test_dare_builder_treats_blank_event_log_path_as_missing(tmp_path) -> None:
    expected_path = tmp_path / ".dare" / "events.db"
    builder = BaseAgent.dare_agent_builder("event-default-blank-path").with_model(_Model())
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "event_log": {"enabled": True, "path": "   "},
        }
    )
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._event_log, TraceAwareEventLog)
    assert isinstance(agent._event_log._inner, SQLiteEventLog)
    assert agent._event_log._inner._path == expected_path


def test_dare_builder_explicit_event_log_overrides_default_autowire(tmp_path) -> None:
    class _ExplicitEventLog:
        async def append(self, event_type: str, payload: dict[str, Any]) -> str:
            _ = (event_type, payload)
            return "event"

        async def query(self, *, filter: dict[str, Any] | None = None, limit: int = 100) -> list[Any]:
            _ = (filter, limit)
            return []

        async def replay(self, *, from_event_id: str) -> Any:
            _ = from_event_id
            return None

        async def verify_chain(self) -> bool:
            return True

    explicit = _ExplicitEventLog()
    builder = (
        BaseAgent.dare_agent_builder("event-explicit")
        .with_model(_Model())
        .with_event_log(explicit)
    )
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "event_log": {"enabled": True, "path": str(tmp_path / ".dare" / "events.db")},
        }
    )
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._event_log, TraceAwareEventLog)
    assert agent._event_log._inner is explicit


@pytest.mark.asyncio
async def test_default_event_log_replay_returns_ordered_session_window(tmp_path) -> None:
    db_path = tmp_path / ".dare" / "events.db"
    builder = BaseAgent.dare_agent_builder("event-replay").with_model(_Model())
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "event_log": {"enabled": True, "path": str(db_path)},
        }
    )
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    result = await agent("replay baseline")
    assert result.success is True

    assert isinstance(agent._event_log, TraceAwareEventLog)
    assert isinstance(agent._event_log._inner, SQLiteEventLog)
    persisted = agent._event_log._inner

    start_events = await persisted.query(filter={"event_type": "session.start"}, limit=1)
    assert len(start_events) == 1

    snapshot = await persisted.replay(from_event_id=start_events[0].event_id)
    assert snapshot.from_event_id == start_events[0].event_id
    assert snapshot.events[0].event_type == "session.start"
    assert any(event.event_type == "session.complete" for event in snapshot.events)

    first_payload = snapshot.events[0].payload
    assert first_payload.get("task_id")
    assert first_payload.get("run_id")
    assert first_payload.get("session_id") == first_payload.get("run_id")
