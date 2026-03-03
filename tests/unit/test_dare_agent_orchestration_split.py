from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from dare_framework.agent._internal.execute_engine import run_execute_loop
from dare_framework.agent._internal.milestone_orchestrator import run_milestone_loop
from dare_framework.agent._internal.orchestration import MilestoneResult, SessionState
from dare_framework.agent._internal.tool_executor import run_tool_loop
from dare_framework.agent.dare_agent import SecurityPreflightResult
from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import DonePredicate, Envelope, Milestone, RunResult, Task, ToolLoopRequest, VerifyResult
from dare_framework.security import PolicyDecision, RiskLevel, TrustedInput
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


class _RecordingBudgetContext:
    def __init__(self, *, assembled: Any | None = None) -> None:
        self.assembled = assembled or SimpleNamespace(messages=[], tools=[], metadata={})
        self.budget_checks = 0
        self.budget_uses: list[tuple[str, int]] = []
        self.stm_messages: list[Any] = []

    def budget_check(self) -> None:
        self.budget_checks += 1

    def budget_use(self, bucket: str, amount: int) -> None:
        self.budget_uses.append((bucket, amount))

    def assemble(self) -> Any:
        return self.assembled

    def stm_add(self, message: Any) -> None:
        self.stm_messages.append(message)


class _RecordingModelAdapter:
    def __init__(self, response: ModelResponse) -> None:
        self.name = "internal-model"
        self.calls = 0
        self.response = response

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        self.calls += 1
        return self.response


class _InternalExecuteAgent:
    def __init__(
        self,
        *,
        model_response: ModelResponse,
        hook_results: dict[HookPhase, HookResult] | None = None,
    ) -> None:
        self._context = _RecordingBudgetContext()
        self._execution_mode = "model_driven"
        self._exec_ctl = None
        self._max_tool_iterations = 2
        self._model = _RecordingModelAdapter(model_response)
        self._hook_results = hook_results or {}
        self.hook_calls: list[tuple[HookPhase, dict[str, Any]]] = []
        self.logged_events: list[tuple[str, dict[str, Any]]] = []
        self.finalized_results: list[dict[str, Any]] = []

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        self.hook_calls.append((phase, dict(payload)))
        return self._hook_results.get(phase, HookResult(decision=HookDecision.ALLOW))

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.logged_events.append((event_type, dict(payload)))

    async def _capability_index(self) -> dict[str, Any]:
        return {}

    async def _run_tool_loop(
        self,
        request: Any,
        *,
        transport: Any | None,
        tool_name: str,
        tool_call_id: str,
        descriptor: Any | None = None,
    ) -> dict[str, Any]:
        raise AssertionError(f"tool loop should not run in this execute test: {request}, {transport}, {tool_name}, {tool_call_id}, {descriptor}")

    async def _run_step_driven_execute_loop(
        self,
        plan: Any,
        execute_start: float,
        *,
        transport: Any | None = None,
    ) -> dict[str, Any]:
        raise AssertionError(f"step-driven path should not run in this execute test: {plan}, {execute_start}, {transport}")

    async def _finalize_execute(self, start_time: float, result: dict[str, Any]) -> dict[str, Any]:
        _ = start_time
        self.finalized_results.append(dict(result))
        return result

    def _apply_context_patch(self, assembled: Any, dispatch: Any) -> tuple[list[Any], list[Any], dict[str, Any]]:
        _ = dispatch
        return list(assembled.messages), list(assembled.tools), dict(assembled.metadata)

    def _apply_model_input_patch(self, model_input: ModelInput, dispatch: Any) -> ModelInput:
        _ = dispatch
        return model_input

    def _context_stats(self, messages: list[Any], tools_count: int) -> dict[str, int]:
        return {"messages_count": len(messages), "tools_count": tools_count}

    def _log(self, message: str) -> None:
        _ = message

    def _log_model_messages(self, messages: list[Any], *, stage: str) -> None:
        _ = (messages, stage)

    def _poll_or_raise(self) -> None:
        return None

    def _record_token_usage(self, usage: dict[str, Any] | None) -> None:
        _ = usage

    def _total_tokens_from_usage(self, usage: dict[str, Any]) -> int:
        _ = usage
        return 0

    def _budget_stats(self) -> dict[str, Any]:
        return {"budget_checks": self._context.budget_checks, "budget_uses": len(self._context.budget_uses)}

    def _is_plan_tool_call(self, name: str | None, descriptor: Any | None) -> bool:
        _ = (name, descriptor)
        return False

    def _is_skill_tool_call(self, descriptor: Any | None) -> bool:
        _ = descriptor
        return False

    def _mount_skill_from_result(self, output: Any) -> None:
        raise AssertionError(f"skill mounting should not run in this execute test: {output}")


class _ToolGatewaySequence:
    def __init__(self, results: list[ToolResult[dict[str, Any]]]) -> None:
        self._results = list(results)
        self.invoke_calls = 0

    async def invoke(self, capability_id: str, approval_ctx: Any, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, approval_ctx, envelope, params)
        self.invoke_calls += 1
        return self._results[min(self.invoke_calls - 1, len(self._results) - 1)]


class _AllowExecuteSafeBoundary:
    async def execute_safe(self, *, action: str, fn: Any, sandbox: Any) -> Any:
        _ = (action, sandbox)
        result = fn()
        if hasattr(result, "__await__"):
            return await result
        return result


class _InternalToolAgent:
    def __init__(
        self,
        *,
        preflight: SecurityPreflightResult,
        gateway_results: list[ToolResult[dict[str, Any]]] | None = None,
        max_calls: int | None = None,
    ) -> None:
        milestone = Milestone(milestone_id="m1", description="tool test", user_input="tool test")
        self._approval_manager = None
        self._context = _RecordingBudgetContext()
        self._governed_tool_gateway = _ToolGatewaySequence(gateway_results or [ToolResult(success=True, output={"ok": True})])
        self._security_boundary = _AllowExecuteSafeBoundary()
        self._session_state = SimpleNamespace(
            run_id="run-1",
            current_milestone_state=SessionState(task_id="task-1", milestone_states=[]).current_milestone_state,
        )
        self._preflight = preflight
        self._max_calls = max_calls
        self.logged_events: list[tuple[str, dict[str, Any]]] = []
        self.hook_calls: list[tuple[HookPhase, dict[str, Any]]] = []
        self.milestone_state = SessionState(task_id="task-1", milestone_states=[]).current_milestone_state
        self._session_state = SimpleNamespace(
            run_id="run-1",
            current_milestone_state=SimpleNamespace(add_evidence=lambda evidence: None),
        )

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        self.hook_calls.append((phase, dict(payload)))
        return HookResult(decision=HookDecision.ALLOW)

    async def _evaluate_tool_security(
        self,
        *,
        request: ToolLoopRequest,
        descriptor: Any | None,
        tool_name: str,
        tool_call_id: str,
        attempt: int,
        requires_approval_override: bool | None = None,
        trusted_risk_level_override: Any | None = None,
    ) -> SecurityPreflightResult:
        _ = (request, descriptor, tool_name, tool_call_id, attempt, requires_approval_override, trusted_risk_level_override)
        return self._preflight

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.logged_events.append((event_type, dict(payload)))

    def _budget_stats(self) -> dict[str, Any]:
        return {"budget_checks": self._context.budget_checks, "budget_uses": len(self._context.budget_uses)}

    def _requires_approval(self, descriptor: Any | None) -> bool:
        _ = descriptor
        return False

    def _risk_level_from_trusted_input(self, trusted_input: TrustedInput) -> int:
        mapping = {
            RiskLevel.READ_ONLY: 1,
            RiskLevel.IDEMPOTENT_WRITE: 2,
            RiskLevel.NON_IDEMPOTENT_EFFECT: 3,
            RiskLevel.COMPENSATABLE: 4,
        }
        return mapping[trusted_input.risk_level]

    def _risk_level_value(self, descriptor: Any | None) -> int:
        _ = descriptor
        return 1

    def _risk_level_value_from_envelope(self, envelope: Any) -> int:
        _ = envelope
        return 1

    def _tool_loop_max_calls(self, envelope: Any) -> int | None:
        _ = envelope
        return self._max_calls


class _RecordingSandbox:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.rolled_back: list[str] = []
        self.committed: list[str] = []

    def create_snapshot(self, context: Any) -> str:
        _ = context
        snapshot_id = f"snap-{len(self.created) + 1}"
        self.created.append(snapshot_id)
        return snapshot_id

    def rollback(self, context: Any, snapshot_id: str) -> None:
        _ = context
        self.rolled_back.append(snapshot_id)

    def commit(self, snapshot_id: str) -> None:
        self.committed.append(snapshot_id)


class _InternalMilestoneAgent:
    def __init__(self, milestone: Milestone) -> None:
        self._context = _RecordingBudgetContext()
        self._session_state = SessionState(task_id="task-1", milestone_states=[])
        self._session_state.milestone_states.append(SimpleNamespace(attempts=0, add_reflection=lambda text: None))
        self._max_milestone_attempts = 1
        self._sandbox = _RecordingSandbox()
        self._remediator = None
        self._milestone = milestone
        self.logged_events: list[tuple[str, dict[str, Any]]] = []
        self.hook_calls: list[tuple[HookPhase, dict[str, Any]]] = []
        self.plan_loop_calls = 0

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        self.hook_calls.append((phase, dict(payload)))
        return HookResult(decision=HookDecision.ALLOW)

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.logged_events.append((event_type, dict(payload)))

    async def _run_plan_loop(self, milestone: Milestone) -> Any:
        assert milestone is self._milestone
        self.plan_loop_calls += 1
        return SimpleNamespace(success=True, steps=[])

    async def _run_execute_loop(self, plan: Any, *, transport: Any | None = None) -> dict[str, Any]:
        raise AssertionError(f"execute loop should not run when plan policy already failed: {plan}, {transport}")

    async def _verify_milestone(self, execute_result: dict[str, Any], validated_plan: Any | None = None) -> VerifyResult:
        raise AssertionError(f"verify should not run when plan policy already failed: {execute_result}, {validated_plan}")

    async def _check_plan_policy(self, milestone: Milestone, validated_plan: Any | None) -> tuple[str | None, str]:
        assert milestone is self._milestone
        _ = validated_plan
        return "execute plan denied by security policy", "deny"

    def _budget_stats(self) -> dict[str, Any]:
        return {"budget_checks": self._context.budget_checks}

    def _log(self, message: str) -> None:
        _ = message


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


@pytest.mark.asyncio
async def test_run_execute_loop_returns_policy_error_when_before_model_hook_blocks() -> None:
    agent = _InternalExecuteAgent(
        model_response=ModelResponse(content="unused", tool_calls=[]),
        hook_results={
            HookPhase.BEFORE_MODEL: HookResult(decision=HookDecision.BLOCK),
        },
    )

    result = await run_execute_loop(agent, None)

    assert result["success"] is False
    assert result["errors"] == ["model invocation denied by hook policy"]
    assert agent._model.calls == 0
    assert any(phase is HookPhase.BEFORE_MODEL for phase, _ in agent.hook_calls)


@pytest.mark.asyncio
async def test_run_execute_loop_returns_content_when_model_has_no_tool_calls() -> None:
    agent = _InternalExecuteAgent(
        model_response=ModelResponse(content="final answer", tool_calls=[]),
    )

    result = await run_execute_loop(agent, None)

    assert result["success"] is True
    assert result["outputs"] == [{"content": "final answer"}]
    assert len(agent._context.stm_messages) == 1
    assert agent._context.stm_messages[0].role == "assistant"
    assert agent._context.stm_messages[0].content == "final answer"


@pytest.mark.asyncio
async def test_run_tool_loop_returns_not_allow_when_preflight_denies() -> None:
    agent = _InternalToolAgent(
        preflight=SecurityPreflightResult(
            trusted_input=TrustedInput(params={"text": "blocked"}, risk_level=RiskLevel.READ_ONLY),
            decision=PolicyDecision.DENY,
            reason="security policy denied capability 'tool.echo'",
        ),
    )
    request = ToolLoopRequest(capability_id="tool.echo", params={"text": "blocked"})

    result = await run_tool_loop(agent, request, transport=None, tool_name="echo", tool_call_id="call-1")

    assert result["success"] is False
    assert result["status"] == "not_allow"
    assert result["error"] == "security policy denied capability 'tool.echo'"
    assert any(event_type == "security.policy_denied" for event_type, _ in agent.logged_events)


@pytest.mark.asyncio
async def test_run_tool_loop_retries_until_done_predicate_is_satisfied() -> None:
    agent = _InternalToolAgent(
        preflight=SecurityPreflightResult(
            trusted_input=TrustedInput(params={"text": "retry"}, risk_level=RiskLevel.READ_ONLY),
            decision=PolicyDecision.ALLOW,
            reason=None,
        ),
        gateway_results=[
            ToolResult(success=True, output={"stage": 1}),
            ToolResult(success=True, output={"done": True}),
        ],
        # Keep max_calls above the expected completion point so the assertion
        # proves the loop exits on the done predicate rather than budget exhaustion.
        max_calls=3,
    )
    request = ToolLoopRequest(
        capability_id="tool.echo",
        params={"text": "retry"},
        envelope=Envelope(done_predicate=DonePredicate(required_keys=["done"])),
    )

    result = await run_tool_loop(agent, request, transport=None, tool_name="echo", tool_call_id="call-2")

    assert result["success"] is True
    assert result["output"] == {"done": True}
    assert agent._governed_tool_gateway.invoke_calls == 2


@pytest.mark.asyncio
async def test_run_milestone_loop_rolls_back_and_records_policy_failure() -> None:
    milestone = Milestone(milestone_id="m1", description="guarded milestone", user_input="guarded milestone")
    agent = _InternalMilestoneAgent(milestone)

    result = await run_milestone_loop(agent, milestone)

    assert result == MilestoneResult(
        success=False,
        outputs=[],
        errors=["execute plan denied by security policy"],
        verify_result=VerifyResult(success=False, errors=["execute plan denied by security policy"]),
    )
    assert agent._sandbox.rolled_back == ["snap-1"]
    assert any(event_type == "security.plan.policy" for event_type, _ in agent.logged_events)
    assert any(event_type == "milestone.failed" for event_type, _ in agent.logged_events)
