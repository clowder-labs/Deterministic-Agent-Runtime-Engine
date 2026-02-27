from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent, DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import StepResult, ValidatedPlan, ValidatedStep
from dare_framework.security.types import PolicyDecision, RiskLevel, TrustedInput
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

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        self.calls += 1
        return ModelResponse(content="model-path", tool_calls=[])


class _ToolGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=True, output={"ok": True})


class _ChainingToolGateway:
    def __init__(self) -> None:
        self.calls = 0

    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = envelope
        self.calls += 1
        if capability_id == "tool.first":
            return ToolResult(success=True, output={"first": 1})
        previous_output = params.get("_previous_output")
        if not isinstance(previous_output, dict):
            return ToolResult(success=False, error="previous output must be dict")
        return ToolResult(success=True, output={"prev_first": previous_output.get("first")})


class _NoneOutputToolGateway:
    def __init__(self) -> None:
        self.calls = 0

    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any] | None]:
        _ = envelope
        self.calls += 1
        if capability_id == "tool.none":
            return ToolResult(success=True, output=None)
        previous_output = params.get("_previous_output", "missing")
        return ToolResult(success=True, output={"previous_is_none": previous_output is None})


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


class _DenyNonReadOnlyBoundary(_AllowBoundary):
    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        raw_risk = context.get("risk_level", RiskLevel.READ_ONLY)
        if isinstance(raw_risk, str):
            try:
                raw_risk = RiskLevel(raw_risk)
            except ValueError:
                raw_risk = RiskLevel.READ_ONLY
        if not isinstance(raw_risk, RiskLevel):
            raw_risk = RiskLevel.READ_ONLY
        return TrustedInput(params=dict(input), risk_level=raw_risk)

    async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
        _ = resource
        if action != "invoke_tool":
            return PolicyDecision.ALLOW
        risk_level = str(context.get("risk_level", RiskLevel.READ_ONLY.value))
        if risk_level == RiskLevel.READ_ONLY.value:
            return PolicyDecision.ALLOW
        return PolicyDecision.DENY


class _RecordingStepExecutor:
    def __init__(self) -> None:
        self.step_ids: list[str] = []

    async def execute_step(
        self,
        step: ValidatedStep,
        ctx: Any,
        previous_results: list[StepResult],
    ) -> StepResult:
        _ = (ctx, previous_results)
        self.step_ids.append(step.step_id)
        return StepResult(
            step_id=step.step_id,
            success=True,
            output={"step": step.step_id},
        )


class _BlockingBeforeToolHook:
    def __init__(self) -> None:
        self.phases: list[HookPhase] = []

    @property
    def name(self) -> str:
        return "blocking-before-tool-hook"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = (args, kwargs)
        self.phases.append(phase)
        if phase is HookPhase.BEFORE_TOOL:
            return HookResult(decision=HookDecision.BLOCK)
        return HookResult(decision=HookDecision.ALLOW)


class _NoOpPlanner:
    async def plan(self, context: Any) -> Any:
        _ = context
        raise RuntimeError("planner should not be called in this test")


class _NoOpValidator:
    async def validate_plan(self, plan: Any, ctx: Any) -> ValidatedPlan:
        _ = ctx
        return ValidatedPlan(
            success=True,
            plan_description=str(getattr(plan, "plan_description", "noop")),
            steps=[],
        )

    async def verify_milestone(self, result: Any, ctx: Any, *, plan: ValidatedPlan | None = None) -> Any:
        _ = (result, ctx, plan)
        return {"success": True}


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
                request_id="req-step-executor-approval",
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


def _build_agent(
    *,
    model: _RecordingModel,
    step_executor: _RecordingStepExecutor | None = None,
    execution_mode: str = "model_driven",
    boundary: Any | None = None,
    context: Context | None = None,
    tool_gateway: Any | None = None,
    planner: Any | None = None,
    validator: Any | None = None,
    approval_manager: Any | None = None,
    hooks: list[Any] | None = None,
    auto_wire_step_driven_defaults: bool = True,
) -> DareAgent:
    normalized_execution_mode = execution_mode.strip().lower()
    if auto_wire_step_driven_defaults and normalized_execution_mode == "step_driven" and planner is None:
        planner = _NoOpPlanner()
        if validator is None:
            validator = _NoOpValidator()
    return DareAgent(
        name="step-mode-agent",
        model=model,
        context=context or Context(config=Config()),
        tool_gateway=tool_gateway or _ToolGateway(),
        planner=planner,
        validator=validator,
        step_executor=step_executor,
        execution_mode=execution_mode,
        security_boundary=boundary,
        approval_manager=approval_manager,
        hooks=hooks,
    )


@pytest.mark.asyncio
async def test_step_driven_execute_loop_runs_validated_steps_in_order() -> None:
    model = _RecordingModel()
    step_executor = _RecordingStepExecutor()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
    )

    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.one", risk_level=RiskLevel.READ_ONLY),
            ValidatedStep(step_id="s2", capability_id="tool.two", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert step_executor.step_ids == ["s1", "s2"]
    assert result["outputs"] == [{"step": "s1"}, {"step": "s2"}]
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_execute_loop_fails_without_validated_plan() -> None:
    model = _RecordingModel()
    step_executor = _RecordingStepExecutor()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
    )

    result = await agent._run_execute_loop(None)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is False
    assert any("validated plan" in error for error in result.get("errors", []))
    assert model.calls == 0


@pytest.mark.asyncio
async def test_default_execution_mode_remains_model_driven() -> None:
    model = _RecordingModel()
    agent = _build_agent(model=model)

    result = await agent._run_execute_loop(None)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert model.calls == 1


@pytest.mark.asyncio
async def test_builder_wires_execution_mode_and_step_executor() -> None:
    model = _RecordingModel()
    step_executor = _RecordingStepExecutor()

    agent = (
        BaseAgent.dare_agent_builder("builder-step-mode")
        .with_model(model)
        .with_execution_mode("step_driven")
        .with_planner(_NoOpPlanner())
        .add_validators(_NoOpValidator())
        .with_step_executor(step_executor)
        .build()
    )
    agent = await agent

    assert getattr(agent, "_execution_mode") == "step_driven"
    assert getattr(agent, "_step_executor") is step_executor


def test_constructor_rejects_step_driven_without_planner() -> None:
    model = _RecordingModel()
    with pytest.raises(ValueError, match="step_driven execution requires planner"):
        _build_agent(
            model=model,
            execution_mode="step_driven",
            validator=_NoOpValidator(),
            auto_wire_step_driven_defaults=False,
        )


def test_constructor_rejects_step_driven_planner_without_validator() -> None:
    model = _RecordingModel()
    with pytest.raises(ValueError, match="step_driven execution with planner requires validator"):
        _build_agent(
            model=model,
            planner=_NoOpPlanner(),
            execution_mode="step_driven",
            auto_wire_step_driven_defaults=False,
        )


@pytest.mark.asyncio
async def test_builder_rejects_step_driven_without_planner() -> None:
    model = _RecordingModel()
    with pytest.raises(ValueError, match="step_driven execution requires planner"):
        await (
            BaseAgent.dare_agent_builder("builder-step-mode-no-planner")
            .with_model(model)
            .with_execution_mode("step_driven")
            .add_validators(_NoOpValidator())
            .build()
        )


@pytest.mark.asyncio
async def test_builder_rejects_step_driven_planner_without_validator() -> None:
    model = _RecordingModel()
    with pytest.raises(ValueError, match="step_driven execution with planner requires validator"):
        await (
            BaseAgent.dare_agent_builder("builder-step-mode-no-validator")
            .with_model(model)
            .with_execution_mode("step_driven")
            .with_planner(_NoOpPlanner())
            .build()
        )


@pytest.mark.asyncio
async def test_builder_wires_security_boundary() -> None:
    model = _RecordingModel()
    boundary = _DenyToolBoundary()

    agent = (
        BaseAgent.dare_agent_builder("builder-security-boundary")
        .with_model(model)
        .with_security_boundary(boundary)
        .build()
    )
    agent = await agent

    assert getattr(agent, "_security_boundary") is boundary


@pytest.mark.asyncio
async def test_step_driven_default_executor_routes_through_security_policy() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    agent = _build_agent(
        model=model,
        execution_mode="step_driven",
        boundary=_DenyToolBoundary(),
        context=context,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.one", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is False
    assert any("security policy" in error for error in result.get("errors", []))
    assert context.budget.used_tool_calls == 1
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_uses_step_risk_level_when_descriptor_missing() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    agent = _build_agent(
        model=model,
        execution_mode="step_driven",
        boundary=_DenyNonReadOnlyBoundary(),
        context=context,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(
                step_id="s1",
                capability_id="tool.one",
                risk_level=RiskLevel.NON_IDEMPOTENT_EFFECT,
            ),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is False
    assert any("security policy" in error for error in result.get("errors", []))
    assert context.budget.used_tool_calls == 1
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_passes_plain_previous_output_between_steps() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    gateway = _ChainingToolGateway()
    agent = _build_agent(
        model=model,
        execution_mode="step_driven",
        boundary=_AllowBoundary(),
        context=context,
        tool_gateway=gateway,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.first", risk_level=RiskLevel.READ_ONLY),
            ValidatedStep(step_id="s2", capability_id="tool.second", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert result["outputs"] == [{"first": 1}, {"prev_first": 1}]
    assert gateway.calls == 2
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_preserves_none_output_between_steps() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    gateway = _NoneOutputToolGateway()
    agent = _build_agent(
        model=model,
        execution_mode="step_driven",
        boundary=_AllowBoundary(),
        context=context,
        tool_gateway=gateway,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="none-output plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.none", risk_level=RiskLevel.READ_ONLY),
            ValidatedStep(step_id="s2", capability_id="tool.inspect", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert result["outputs"] == [None, {"previous_is_none": True}]
    assert gateway.calls == 2
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_custom_executor_still_tracks_tool_call_budget() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    step_executor = _RecordingStepExecutor()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
        boundary=_AllowBoundary(),
        context=context,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.one", risk_level=RiskLevel.READ_ONLY),
            ValidatedStep(step_id="s2", capability_id="tool.two", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert context.budget.used_tool_calls == 2


@pytest.mark.asyncio
async def test_step_driven_custom_executor_respects_security_policy() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    step_executor = _RecordingStepExecutor()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
        boundary=_DenyToolBoundary(),
        context=context,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.one", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is False
    assert any("security policy" in error for error in result.get("errors", []))
    assert step_executor.step_ids == []
    assert context.budget.used_tool_calls == 1
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_custom_executor_requires_metadata_approval_under_allow_policy() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    step_executor = _RecordingStepExecutor()
    approval_manager = _PendingAllowApprovalManager()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
        boundary=_AllowBoundary(),
        context=context,
        approval_manager=approval_manager,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(
                step_id="s1",
                capability_id="tool.one",
                risk_level=RiskLevel.READ_ONLY,
                metadata={"requires_approval": True},
            ),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert step_executor.step_ids == ["s1"]
    assert approval_manager.evaluate_calls == 1
    assert approval_manager.wait_calls == 1
    assert context.budget.used_tool_calls == 1
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_custom_executor_approve_required_with_metadata_routes_to_approval_workflow() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    step_executor = _RecordingStepExecutor()
    approval_manager = _PendingAllowApprovalManager()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
        boundary=_ApproveToolBoundary(),
        context=context,
        approval_manager=approval_manager,
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(
                step_id="s1",
                capability_id="tool.one",
                risk_level=RiskLevel.READ_ONLY,
                metadata={"requires_approval": True},
            ),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is True
    assert step_executor.step_ids == ["s1"]
    assert approval_manager.evaluate_calls == 1
    assert approval_manager.wait_calls == 1
    assert context.budget.used_tool_calls == 1
    assert model.calls == 0


@pytest.mark.asyncio
async def test_step_driven_custom_executor_respects_before_tool_hook_policy() -> None:
    model = _RecordingModel()
    context = Context(config=Config())
    step_executor = _RecordingStepExecutor()
    hook = _BlockingBeforeToolHook()
    agent = _build_agent(
        model=model,
        step_executor=step_executor,
        execution_mode="step_driven",
        boundary=_AllowBoundary(),
        context=context,
        hooks=[hook],
    )
    validated_plan = ValidatedPlan(
        success=True,
        plan_description="step plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.one", risk_level=RiskLevel.READ_ONLY),
        ],
    )

    result = await agent._run_execute_loop(validated_plan)  # noqa: SLF001 - runtime unit boundary test

    assert result["success"] is False
    assert any("hook policy" in error for error in result.get("errors", []))
    assert step_executor.step_ids == []
    assert HookPhase.BEFORE_TOOL in hook.phases
    assert HookPhase.AFTER_TOOL in hook.phases
