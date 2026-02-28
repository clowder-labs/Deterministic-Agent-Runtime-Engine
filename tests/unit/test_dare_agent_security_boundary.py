from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType
from dare_framework.plan.types import (
    DonePredicate,
    Envelope,
    ProposedPlan,
    Task,
    ToolLoopRequest,
    ValidatedPlan,
)
from dare_framework.security import PolicyDecision, RiskLevel, TrustedInput
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluation,
    ApprovalEvaluationStatus,
    PendingApprovalRequest,
)
from dare_framework.tool.types import ToolResult


class _RecordingModel:
    name = "recording-model"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, model_input: Any, *, options: Any = None) -> Any:
        _ = (model_input, options)
        self.calls += 1
        from dare_framework.model.types import ModelResponse

        return ModelResponse(content="ok", tool_calls=[])


class _RecordingToolGateway:
    def __init__(self) -> None:
        self.invoke_calls = 0
        self.last_params: dict[str, Any] | None = None

    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope)
        self.invoke_calls += 1
        self.last_params = dict(params)
        return ToolResult(success=True, output={"ok": True})


class _TwoStageDoneToolGateway:
    def __init__(self) -> None:
        self.invoke_calls = 0

    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        self.invoke_calls += 1
        if self.invoke_calls == 1:
            return ToolResult(success=True, output={"stage": 1})
        return ToolResult(success=True, output={"done": True})


class _AllowBoundary:
    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        _ = context
        return TrustedInput(params=dict(input), risk_level=RiskLevel.READ_ONLY)

    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = (action, resource, context)
        return PolicyDecision.ALLOW

    async def execute_safe(self, *, action: str, fn: Any, sandbox: Any) -> Any:
        _ = (action, sandbox)
        value = fn()
        if hasattr(value, "__await__"):
            return await value
        return value


class _DenyToolBoundary(_AllowBoundary):
    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = (resource, context)
        if action == "invoke_tool":
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW


class _ApproveToolBoundary(_AllowBoundary):
    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = (resource, context)
        if action == "invoke_tool":
            return PolicyDecision.APPROVE_REQUIRED
        return PolicyDecision.ALLOW


class _TrustRewriteBoundary(_AllowBoundary):
    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        _ = (input, context)
        return TrustedInput(
            params={"trusted": "yes"},
            risk_level=RiskLevel.IDEMPOTENT_WRITE,
            metadata={"source": "policy"},
        )


class _PlanDenyBoundary(_AllowBoundary):
    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = (resource, context)
        if action == "execute_plan":
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW


class _PlanApproveRequiredBoundary(_AllowBoundary):
    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = (resource, context)
        if action == "execute_plan":
            return PolicyDecision.APPROVE_REQUIRED
        return PolicyDecision.ALLOW


class _PlanPolicyCrashBoundary(_AllowBoundary):
    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = (resource, context)
        if action == "execute_plan":
            raise RuntimeError("plan policy backend unavailable")
        return PolicyDecision.ALLOW


class _TrustFailureBoundary(_AllowBoundary):
    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        _ = (input, context)
        raise RuntimeError("trust backend unavailable")


class _MetadataSpoofBoundary(_AllowBoundary):
    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        _ = context
        return TrustedInput(
            params=dict(input),
            risk_level=RiskLevel.NON_IDEMPOTENT_EFFECT,
            metadata={
                # Must never override canonical policy context fields.
                "risk_level": RiskLevel.READ_ONLY.value,
                "capability_id": "spoofed-capability",
                "tool_name": "spoofed-tool",
            },
        )

    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = resource
        if action != "invoke_tool":
            return PolicyDecision.ALLOW
        # Deny only when canonical values are preserved; if metadata can spoof
        # these keys, this branch will be bypassed.
        if (
            context.get("risk_level") == RiskLevel.NON_IDEMPOTENT_EFFECT.value
            and context.get("capability_id") == "tool.echo"
            and context.get("tool_name") == "echo"
        ):
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW


class _Planner:
    async def plan(self, ctx: Any) -> ProposedPlan:
        _ = ctx
        return ProposedPlan(plan_description="plan", steps=[], attempt=1)

    async def decompose(self, task: Task, ctx: Any) -> Any:
        _ = ctx
        from dare_framework.plan.types import DecompositionResult

        return DecompositionResult(
            milestones=task.to_milestones(),
            reasoning="unit-test decomposition",
        )


class _Validator:
    async def validate_plan(self, plan: ProposedPlan, ctx: Any) -> ValidatedPlan:
        _ = (plan, ctx)
        return ValidatedPlan(success=True, plan_description="validated", steps=[])

    async def verify_milestone(self, result: Any, ctx: Any, *, plan: ValidatedPlan | None = None) -> Any:
        _ = (result, ctx, plan)
        from dare_framework.plan.types import VerifyResult

        return VerifyResult(success=True)


class _RecordingEventLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        self.events.append((event_type, dict(payload)))
        return f"evt-{len(self.events)}"


class _RecordingPhaseHook:
    def __init__(self) -> None:
        self.phases: list[HookPhase] = []
        self.payloads: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "recording-phase-hook"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = args
        payload = kwargs.get("payload", {})
        self.phases.append(phase)
        self.payloads.append(payload if isinstance(payload, dict) else {})
        return HookResult(decision=HookDecision.ALLOW)


class _BlockingBeforeToolHook:
    @property
    def name(self) -> str:
        return "blocking-before-tool-hook"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = (args, kwargs)
        if phase is HookPhase.BEFORE_TOOL:
            return HookResult(decision=HookDecision.BLOCK)
        return HookResult(decision=HookDecision.ALLOW)


class _PendingAllowApprovalManager:
    def __init__(self) -> None:
        self.evaluate_calls = 0
        self.wait_calls = 0

    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        self.evaluate_calls += 1
        return ApprovalEvaluation(
            status=ApprovalEvaluationStatus.PENDING,
            request=PendingApprovalRequest(
                request_id="req-security-ask",
                capability_id=capability_id,
                params=dict(params),
                params_hash="hash",
                command=None,
                session_id=session_id,
                reason=reason,
                created_at=0.0,
            ),
            reason="approval required",
        )

    async def wait_for_resolution(
        self,
        request_id: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ApprovalDecision:
        _ = (request_id, timeout_seconds)
        self.wait_calls += 1
        return ApprovalDecision.ALLOW


class _EvaluateErrorApprovalManager:
    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        _ = (capability_id, params, session_id, reason)
        raise RuntimeError("approval backend unavailable")


class _PendingWaitErrorApprovalManager:
    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        return ApprovalEvaluation(
            status=ApprovalEvaluationStatus.PENDING,
            request=PendingApprovalRequest(
                request_id="req-security-ask-wait-error",
                capability_id=capability_id,
                params=dict(params),
                params_hash="hash",
                command=None,
                session_id=session_id,
                reason=reason,
                created_at=0.0,
            ),
            reason="approval required",
        )

    async def wait_for_resolution(
        self,
        request_id: str,
        *,
        timeout_seconds: float | None = None,
    ) -> ApprovalDecision:
        _ = (request_id, timeout_seconds)
        raise RuntimeError("approval wait channel unavailable")


class _RuleDenyApprovalManager:
    def __init__(self) -> None:
        self.evaluate_calls = 0

    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        _ = (capability_id, params, session_id, reason)
        self.evaluate_calls += 1
        return ApprovalEvaluation(status=ApprovalEvaluationStatus.DENY, reason="rule denied")


def _build_agent(
    *,
    boundary: Any,
    model: _RecordingModel | None = None,
    planner: Any | None = None,
    validator: Any | None = None,
    tool_gateway: _RecordingToolGateway | None = None,
    event_log: Any | None = None,
    hooks: list[Any] | None = None,
    approval_manager: Any | None = None,
) -> DareAgent:
    return DareAgent(
        name="security-agent",
        model=model or _RecordingModel(),
        context=Context(config=Config()),
        tool_gateway=tool_gateway or _RecordingToolGateway(),
        planner=planner,
        validator=validator,
        security_boundary=boundary,
        event_log=event_log,
        hooks=hooks,
        approval_manager=approval_manager,
    )


@pytest.mark.asyncio
async def test_tool_loop_denied_by_security_policy() -> None:
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(boundary=_DenyToolBoundary(), tool_gateway=tool_gateway)

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-deny",
    )

    assert result["success"] is False
    assert result["status"] == "not_allow"
    assert "security policy" in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_tool_loop_approve_required_without_execution_control_fails() -> None:
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(boundary=_ApproveToolBoundary(), tool_gateway=tool_gateway)

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-ask",
    )

    assert result["success"] is False
    assert "approval manager" in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_tool_loop_before_tool_hook_blocks_before_metadata_approval_resolution() -> None:
    tool_gateway = _RecordingToolGateway()
    hook = _BlockingBeforeToolHook()
    agent = _build_agent(
        boundary=_AllowBoundary(),
        tool_gateway=tool_gateway,
        hooks=[hook],
    )

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-hook-before-approval",
        requires_approval_override=True,
    )

    assert result["success"] is False
    assert "hook policy" in str(result["error"])
    assert "approval manager" not in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_tool_loop_approve_required_routes_through_approval_workflow() -> None:
    tool_gateway = _RecordingToolGateway()
    approval_manager = _PendingAllowApprovalManager()
    agent = _build_agent(
        boundary=_ApproveToolBoundary(),
        tool_gateway=tool_gateway,
        approval_manager=approval_manager,
    )

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-ask-approval-flow",
    )

    assert result["success"] is True
    assert tool_gateway.invoke_calls == 1
    assert approval_manager.evaluate_calls == 1
    assert approval_manager.wait_calls == 1


@pytest.mark.asyncio
async def test_tool_loop_approval_evaluate_exception_returns_structured_failure() -> None:
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(
        boundary=_ApproveToolBoundary(),
        tool_gateway=tool_gateway,
        approval_manager=_EvaluateErrorApprovalManager(),
    )

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-approval-evaluate-error",
    )

    assert result["success"] is False
    assert "approval evaluation failed" in str(result["error"])
    assert "approval backend unavailable" in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_tool_loop_approval_wait_exception_returns_structured_failure() -> None:
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(
        boundary=_ApproveToolBoundary(),
        tool_gateway=tool_gateway,
        approval_manager=_PendingWaitErrorApprovalManager(),
    )

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-approval-wait-error",
    )

    assert result["success"] is False
    assert "approval resolution failed" in str(result["error"])
    assert "approval wait channel unavailable" in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_tool_loop_policy_approve_required_rechecks_approval_on_retry() -> None:
    tool_gateway = _TwoStageDoneToolGateway()
    approval_manager = _PendingAllowApprovalManager()
    agent = _build_agent(
        boundary=_ApproveToolBoundary(),
        tool_gateway=tool_gateway,  # type: ignore[arg-type]
        approval_manager=approval_manager,
    )

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(
            capability_id="tool.echo",
            params={"value": 1},
            envelope=Envelope(done_predicate=DonePredicate(required_keys=["done"])),
        ),
        tool_name="echo",
        tool_call_id="tc-security-approval-retry",
    )

    assert result["success"] is True
    assert tool_gateway.invoke_calls == 2
    # Policy-driven approval requirement should be enforced on each retry.
    assert approval_manager.evaluate_calls == 2
    assert approval_manager.wait_calls == 2


@pytest.mark.asyncio
async def test_tool_loop_policy_approval_deny_preserves_not_allow_status() -> None:
    tool_gateway = _RecordingToolGateway()
    approval_manager = _RuleDenyApprovalManager()
    agent = _build_agent(
        boundary=_ApproveToolBoundary(),
        tool_gateway=tool_gateway,
        approval_manager=approval_manager,
    )

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-approval-deny-status",
    )

    assert result["success"] is False
    assert result["status"] == "not_allow"
    assert "approval rule" in str(result["error"])
    assert approval_manager.evaluate_calls == 1
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_tool_loop_uses_trusted_params_from_security_boundary() -> None:
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(boundary=_TrustRewriteBoundary(), tool_gateway=tool_gateway)

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"raw": "no"}),
        tool_name="echo",
        tool_call_id="tc-security-trust",
    )

    assert result["success"] is True
    assert tool_gateway.invoke_calls == 1
    assert tool_gateway.last_params is not None
    assert tool_gateway.last_params.get("trusted") == "yes"


@pytest.mark.asyncio
async def test_plan_entry_denied_by_security_policy_stops_before_execute() -> None:
    model = _RecordingModel()
    agent = _build_agent(
        boundary=_PlanDenyBoundary(),
        model=model,
        planner=_Planner(),
        validator=_Validator(),
    )

    result = await agent("run guarded task")

    assert result.success is False
    assert any("execute plan denied by security policy" in str(err) for err in result.errors)
    assert model.calls == 0


@pytest.mark.asyncio
async def test_plan_policy_failure_emits_after_milestone_and_precise_decision() -> None:
    model = _RecordingModel()
    event_log = _RecordingEventLog()
    hook = _RecordingPhaseHook()
    agent = _build_agent(
        boundary=_PlanApproveRequiredBoundary(),
        model=model,
        planner=_Planner(),
        validator=_Validator(),
        event_log=event_log,
        hooks=[hook],
    )

    result = await agent("run guarded task")

    assert result.success is False
    assert any("security approval" in str(err) for err in result.errors)
    policy_events = [payload for event_type, payload in event_log.events if event_type == "security.plan.policy"]
    assert policy_events
    assert policy_events[-1].get("decision") == "approve_required"
    assert any(event_type == "milestone.failed" for event_type, _ in event_log.events)
    assert HookPhase.AFTER_MILESTONE in hook.phases
    assert model.calls == 0


@pytest.mark.asyncio
async def test_tool_loop_security_boundary_exception_returns_structured_failure() -> None:
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(boundary=_TrustFailureBoundary(), tool_gateway=tool_gateway)

    result = await agent._run_tool_loop(  # noqa: SLF001
        ToolLoopRequest(capability_id="tool.echo", params={"value": 1}),
        tool_name="echo",
        tool_call_id="tc-security-error",
    )

    assert result["success"] is False
    assert "trust backend unavailable" in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_plan_policy_exception_returns_structured_milestone_failure() -> None:
    model = _RecordingModel()
    event_log = _RecordingEventLog()
    hook = _RecordingPhaseHook()
    agent = _build_agent(
        boundary=_PlanPolicyCrashBoundary(),
        model=model,
        planner=_Planner(),
        validator=_Validator(),
        event_log=event_log,
        hooks=[hook],
    )

    result = await agent("run guarded task")

    assert result.success is False
    assert any("plan policy backend unavailable" in str(err) for err in result.errors)
    policy_events = [payload for event_type, payload in event_log.events if event_type == "security.plan.policy"]
    assert policy_events
    assert policy_events[-1].get("decision") == "error"
    assert any(event_type == "milestone.failed" for event_type, _ in event_log.events)
    assert HookPhase.AFTER_MILESTONE in hook.phases


@pytest.mark.asyncio
async def test_tool_policy_context_preserves_canonical_fields_over_metadata() -> None:
    agent = _build_agent(boundary=_MetadataSpoofBoundary())

    trusted_params, trust_error = await agent._resolve_tool_security(  # noqa: SLF001
        capability_id="tool.echo",
        params={"value": 1},
        tool_name="echo",
        risk_level=3,
        requires_approval=False,
    )

    assert trusted_params == {}
    assert "security policy" in str(trust_error)


@pytest.mark.asyncio
async def test_plan_policy_check_skipped_when_plan_is_absent() -> None:
    model = _RecordingModel()
    event_log = _RecordingEventLog()
    agent = _build_agent(
        boundary=_PlanDenyBoundary(),
        model=model,
        event_log=event_log,
    )

    result = await agent("run task without planner")

    assert result.success is True
    assert model.calls == 1
    policy_events = [payload for event_type, payload in event_log.events if event_type == "security.plan.policy"]
    assert policy_events == []
