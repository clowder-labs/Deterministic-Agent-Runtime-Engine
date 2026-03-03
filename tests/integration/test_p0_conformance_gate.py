from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.event import SQLiteEventLog
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import (
    DecompositionResult,
    Milestone,
    ProposedPlan,
    RunResult,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
)
from dare_framework.security import PolicySecurityBoundary
from dare_framework.security.types import RiskLevel
from dare_framework.tool.types import CapabilityDescriptor, CapabilityType, ToolResult


class _NeverCalledModel:
    name = "never-called-model"

    async def generate(self, *_: Any, **__: Any) -> Any:
        raise RuntimeError("step-driven integration should not use the model execute loop")


class _SingleToolCallModel:
    name = "single-tool-call-model"

    def __init__(self) -> None:
        self._responses = [
            ModelResponse(
                content="invoke audit tool",
                tool_calls=[
                    {
                        "id": "tc-audit-1",
                        "name": "tool.echo",
                        "capability_id": "tool.echo",
                        "arguments": {"text": "hi"},
                    }
                ],
            ),
            ModelResponse(content="done", tool_calls=[]),
        ]

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        if self._responses:
            return self._responses.pop(0)
        return ModelResponse(content="done", tool_calls=[])


@dataclass
class _PlannerRecord:
    decompose_calls: int = 0
    plan_calls: int = 0


class _StepDrivenPlanner:
    def __init__(self) -> None:
        self.record = _PlannerRecord()

    async def decompose(self, task: Any, ctx: Any) -> DecompositionResult:
        _ = ctx
        self.record.decompose_calls += 1
        return DecompositionResult(
            milestones=[
                Milestone(
                    milestone_id="milestone-step-driven",
                    description=task.description,
                    user_input=task.description,
                )
            ],
            reasoning="single milestone for integration coverage",
        )

    async def plan(self, ctx: Any) -> ProposedPlan:
        _ = ctx
        self.record.plan_calls += 1
        return ProposedPlan(plan_description="proposed step-driven plan")


@dataclass
class _VerifyCall:
    success: bool
    errors: list[str]
    output: Any
    plan_step_ids: list[str]


class _StaticValidator:
    def __init__(self, validated_plan: ValidatedPlan) -> None:
        self._validated_plan = validated_plan
        self.validate_calls = 0
        self.verify_calls: list[_VerifyCall] = []

    async def validate_plan(self, plan: ProposedPlan, ctx: Any) -> ValidatedPlan:
        _ = (plan, ctx)
        self.validate_calls += 1
        return self._validated_plan

    async def verify_milestone(
        self,
        result: RunResult,
        ctx: Any,
        *,
        plan: ValidatedPlan | None = None,
    ) -> VerifyResult:
        _ = ctx
        self.verify_calls.append(
            _VerifyCall(
                success=result.success,
                errors=list(result.errors),
                output=result.output,
                plan_step_ids=[step.step_id for step in plan.steps] if plan is not None else [],
            )
        )
        return VerifyResult(success=result.success, errors=list(result.errors))


class _RecordingGateway:
    def __init__(self, results: dict[str, ToolResult[Any]]) -> None:
        self._results = dict(results)
        self._descriptors = [
            CapabilityDescriptor(
                id=capability_id,
                type=CapabilityType.TOOL,
                name=capability_id,
                description=capability_id,
                input_schema={"type": "object"},
                metadata={"risk_level": RiskLevel.READ_ONLY.value},
            )
            for capability_id in results
        ]
        self.invoke_calls: list[dict[str, Any]] = []

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return list(self._descriptors)

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[Any]:
        self.invoke_calls.append(
            {
                "capability_id": capability_id,
                "envelope": envelope,
                "params": dict(params),
            }
        )
        return self._results[capability_id]


class _EchoGateway:
    def __init__(self) -> None:
        self._descriptor = CapabilityDescriptor(
            id="tool.echo",
            type=CapabilityType.TOOL,
            name="tool.echo",
            description="echo tool",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            metadata={"risk_level": RiskLevel.READ_ONLY.value},
        )

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return [self._descriptor]

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[Any]:
        _ = envelope
        return ToolResult(success=True, output={"echo": params.get("text")})


def _build_step_driven_agent(
    *,
    gateway: _RecordingGateway,
    validator: _StaticValidator,
    planner: _StepDrivenPlanner,
    max_milestone_attempts: int = 1,
) -> DareAgent:
    return DareAgent(
        name="p0-step-driven-agent",
        model=_NeverCalledModel(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        planner=planner,
        validator=validator,
        security_boundary=PolicySecurityBoundary(),
        execution_mode="step_driven",
        max_milestone_attempts=max_milestone_attempts,
        max_plan_attempts=1,
    )


@pytest.mark.asyncio
async def test_step_driven_session_executes_validated_steps_in_order() -> None:
    planner = _StepDrivenPlanner()
    validated_plan = ValidatedPlan(
        plan_description="validated step-driven plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.first", risk_level=RiskLevel.READ_ONLY),
            ValidatedStep(step_id="s2", capability_id="tool.second", risk_level=RiskLevel.READ_ONLY),
        ],
    )
    validator = _StaticValidator(validated_plan)
    gateway = _RecordingGateway(
        {
            "tool.first": ToolResult(success=True, output={"first": 1}),
            "tool.second": ToolResult(success=True, output={"prev_first": 1}),
        }
    )
    agent = _build_step_driven_agent(
        gateway=gateway,
        validator=validator,
        planner=planner,
    )

    result = await agent("run ordered step-driven session")

    assert result.success is True
    assert planner.record.decompose_calls == 1
    assert planner.record.plan_calls == 1
    assert validator.validate_calls == 1
    assert len(validator.verify_calls) == 1
    assert validator.verify_calls[0].plan_step_ids == ["s1", "s2"]
    assert result.session_summary is not None
    assert result.session_summary.milestones[0].outputs == [{"first": 1}, {"prev_first": 1}]
    assert result.session_summary.final_output == {"prev_first": 1}
    assert [call["capability_id"] for call in gateway.invoke_calls] == ["tool.first", "tool.second"]
    assert gateway.invoke_calls[1]["params"]["_previous_output"] == {"first": 1}


@pytest.mark.asyncio
async def test_step_driven_session_stops_after_first_failed_step() -> None:
    planner = _StepDrivenPlanner()
    validated_plan = ValidatedPlan(
        plan_description="validated fail-fast plan",
        steps=[
            ValidatedStep(step_id="s1", capability_id="tool.fail", risk_level=RiskLevel.READ_ONLY),
            ValidatedStep(step_id="s2", capability_id="tool.never", risk_level=RiskLevel.READ_ONLY),
        ],
    )
    validator = _StaticValidator(validated_plan)
    gateway = _RecordingGateway(
        {
            "tool.fail": ToolResult(success=False, error="boom"),
            "tool.never": ToolResult(success=True, output={"unexpected": True}),
        }
    )
    agent = _build_step_driven_agent(
        gateway=gateway,
        validator=validator,
        planner=planner,
    )

    result = await agent("run failing step-driven session")

    assert result.success is False
    assert planner.record.decompose_calls == 1
    assert planner.record.plan_calls == 1
    assert validator.validate_calls == 1
    assert len(validator.verify_calls) == 1
    assert validator.verify_calls[0].success is False
    assert validator.verify_calls[0].errors == ["boom"]
    assert validator.verify_calls[0].plan_step_ids == ["s1", "s2"]
    assert result.session_summary is not None
    assert result.session_summary.milestones[0].outputs == []
    assert [call["capability_id"] for call in gateway.invoke_calls] == ["tool.fail"]
    assert result.errors == ["milestone failed after max attempts"]


@pytest.mark.asyncio
async def test_default_event_log_replay_and_hash_chain_hold_for_runtime_session(tmp_path) -> None:
    db_path = tmp_path / ".dare" / "events.db"
    event_log = SQLiteEventLog(db_path)
    agent = DareAgent(
        name="p0-audit-agent",
        model=_SingleToolCallModel(),
        context=Context(config=Config()),
        tool_gateway=_EchoGateway(),
        event_log=event_log,
        security_boundary=PolicySecurityBoundary(),
    )

    result = await agent("record auditable runtime session")

    assert result.success is True

    start_events = await event_log.query(filter={"event_type": "session.start"}, limit=1)
    assert len(start_events) == 1

    snapshot = await event_log.replay(from_event_id=start_events[0].event_id)
    assert snapshot.from_event_id == start_events[0].event_id
    assert snapshot.events[0].event_type == "session.start"
    assert any(event.event_type == "security.policy_checked" for event in snapshot.events)
    assert any(event.event_type == "session.complete" for event in snapshot.events)
    for event in snapshot.events:
        assert event.payload.get("task_id")
        assert event.payload.get("run_id")
        assert event.payload.get("session_id") == event.payload.get("run_id")

    assert await event_log.verify_chain() is True

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE events SET payload_json = ? WHERE event_id = ?",
            ('{"tampered":true}', snapshot.events[-1].event_id),
        )
        conn.commit()

    assert await event_log.verify_chain() is False
