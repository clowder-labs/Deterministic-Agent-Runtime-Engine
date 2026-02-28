from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent._internal.orchestration import MilestoneResult, SessionState
from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import Milestone, RunResult, Task, ToolLoopRequest
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
        return ToolResult(success=True, output={"ok": True})


def _build_agent() -> DareAgent:
    return DareAgent(
        name="split-agent",
        model=_Model(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )


@pytest.mark.asyncio
async def test_session_loop_delegates_to_internal_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _build_agent()
    task = Task(description="delegate session")
    expected = RunResult(success=True, output={"delegated": "session"}, errors=[])
    calls: list[tuple[Any, Any, Any]] = []

    async def _fake_runner(inner_agent: Any, inner_task: Task, *, transport: Any | None = None) -> RunResult:
        calls.append((inner_agent, inner_task, transport))
        return expected

    monkeypatch.setattr(
        "dare_framework.agent.dare_agent.run_session_loop",
        _fake_runner,
        raising=False,
    )

    result = await agent._run_session_loop(task)  # noqa: SLF001 - deliberate delegation assertion

    assert result == expected
    assert len(calls) == 1
    assert calls[0][0] is agent
    assert calls[0][1] is task


@pytest.mark.asyncio
async def test_milestone_loop_delegates_to_internal_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _build_agent()
    milestone = Milestone(milestone_id="m1", description="desc", user_input="desc")
    agent._session_state = SessionState(task_id="t1")  # noqa: SLF001 - intentional runtime setup
    expected = MilestoneResult(success=True, outputs=[{"delegated": "milestone"}], errors=[])
    calls: list[tuple[Any, Any, Any]] = []

    async def _fake_runner(inner_agent: Any, inner_milestone: Milestone, *, transport: Any | None = None) -> MilestoneResult:
        calls.append((inner_agent, inner_milestone, transport))
        return expected

    monkeypatch.setattr(
        "dare_framework.agent.dare_agent.run_milestone_loop",
        _fake_runner,
        raising=False,
    )

    result = await agent._run_milestone_loop(milestone)  # noqa: SLF001 - deliberate delegation assertion

    assert result == expected
    assert len(calls) == 1
    assert calls[0][0] is agent
    assert calls[0][1] is milestone


@pytest.mark.asyncio
async def test_execute_loop_delegates_to_internal_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _build_agent()
    expected: dict[str, Any] = {"success": True, "outputs": [{"delegated": "execute"}], "errors": []}
    calls: list[tuple[Any, Any, Any]] = []

    async def _fake_runner(inner_agent: Any, plan: Any, *, transport: Any | None = None) -> dict[str, Any]:
        calls.append((inner_agent, plan, transport))
        return expected

    monkeypatch.setattr(
        "dare_framework.agent.dare_agent.run_execute_loop",
        _fake_runner,
        raising=False,
    )

    result = await agent._run_execute_loop(None)  # noqa: SLF001 - deliberate delegation assertion

    assert result == expected
    assert len(calls) == 1
    assert calls[0][0] is agent
    assert calls[0][1] is None


@pytest.mark.asyncio
async def test_tool_loop_delegates_to_internal_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _build_agent()
    request = ToolLoopRequest(capability_id="tool.echo", params={"text": "hello"})
    expected: dict[str, Any] = {"success": True, "status": "success", "output": {"delegated": "tool"}}
    calls: list[tuple[Any, Any, Any, Any, Any, Any]] = []

    async def _fake_runner(
        inner_agent: Any,
        inner_request: ToolLoopRequest,
        *,
        transport: Any | None,
        tool_name: str,
        tool_call_id: str,
        descriptor: Any | None = None,
    ) -> dict[str, Any]:
        calls.append((inner_agent, inner_request, transport, tool_name, tool_call_id, descriptor))
        return expected

    monkeypatch.setattr(
        "dare_framework.agent.dare_agent.run_tool_loop",
        _fake_runner,
        raising=False,
    )

    result = await agent._run_tool_loop(  # noqa: SLF001 - deliberate delegation assertion
        request,
        tool_name="echo",
        tool_call_id="tc-1",
        descriptor={"d": 1},
    )

    assert result == expected
    assert len(calls) == 1
    assert calls[0][0] is agent
    assert calls[0][1] is request
    assert calls[0][3] == "echo"
    assert calls[0][4] == "tc-1"
    assert calls[0][5] == {"d": 1}
