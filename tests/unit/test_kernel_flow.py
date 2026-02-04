from typing import Any

import pytest

import pytest

pytest.skip(
    "Legacy kernel flow tests are archived; port to canonical dare_framework once "
    "full runtime/orchestrator/tool-loop implementations exist.",
    allow_module_level=True,
)

from dare_framework.plan.impl.planners.deterministic import DeterministicPlanner
from dare_framework.tool.impl.providers.native_tool_provider import NativeToolProvider
from dare_framework.plan.impl.remediators.noop import NoOpRemediator
from dare_framework.tool.impl.tools.noop import NoOpTool
from dare_framework.plan.impl.validators.kernel_validator import GatewayValidator
from dare_framework.contracts.ids import generator_id
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.tool import ITool, ToolResult, ToolType
from dare_framework.execution.types import Budget
from dare_framework.execution.impl.budget.in_memory import InMemoryResourceManager
from dare_framework.context.impl.default_context_manager import DefaultContextManager
from dare_framework.execution.impl.execution_control.file_execution_control import FileExecutionControl
from dare_framework.execution.impl.event.local_event_log import LocalEventLog
from dare_framework.execution.impl.hook.default_extension_point import DefaultExtensionPoint
from dare_framework.execution.impl.orchestrator.default_orchestrator import DefaultLoopOrchestrator
from dare_framework.execution.impl.run_loop.default_run_loop import DefaultRunLoop
from dare_framework.security.impl.default_security_boundary import DefaultSecurityBoundary
from dare_framework.tool.impl.default_tool_gateway import DefaultToolGateway
from dare_framework.tool.types import RunContext
from dare_framework.plan.envelope import DonePredicate, Envelope, EvidenceCondition, ToolLoopRequest
from dare_framework.plan.planning import ProposedStep
from dare_framework.security.types import PolicyDecision
from dare_framework.plan.task import Task


@pytest.mark.asyncio
async def test_plan_tool_triggers_replan_then_succeeds(tmp_path):
    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))
    run_context = RunContext()

    tools = [NoOpTool()]
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(NativeToolProvider(tools=tools, context_factory=lambda: run_context))

    planner = DeterministicPlanner(
        [
            [ProposedStep(step_id=generator_id("step"), capability_id="plan:replan", params={})],
            [ProposedStep(step_id=generator_id("step"), capability_id="tool:noop", params={})],
        ]
    )
    validator = GatewayValidator(tool_gateway)

    orchestrator = DefaultLoopOrchestrator(
        planner=planner,
        validator=validator,
        remediator=NoOpRemediator(),
        model_adapter=None,
        context_manager=DefaultContextManager(),
        tool_gateway=tool_gateway,
        security_boundary=DefaultSecurityBoundary(),
        execution_control=FileExecutionControl(event_log=event_log, checkpoint_dir=str(tmp_path / "checkpoints")),
        resource_manager=InMemoryResourceManager(default_budget=Budget(max_tool_calls=20, max_time_seconds=5)),
        event_log=event_log,
        extension_point=DefaultExtensionPoint(),
        run_context_state=run_context,
    )
    run_loop = DefaultRunLoop(orchestrator)

    result = await run_loop.run(Task(description="noop"))
    assert result.success is True
    assert result.milestone_results[0].summary is not None
    assert result.milestone_results[0].summary.attempt_count == 2


@pytest.mark.asyncio
async def test_tool_loop_enforces_done_predicate_and_budget(tmp_path):
    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))
    run_context = RunContext()

    tools = [NoOpTool()]
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(NativeToolProvider(tools=tools, context_factory=lambda: run_context))

    orchestrator = DefaultLoopOrchestrator(
        planner=DeterministicPlanner([]),
        validator=GatewayValidator(tool_gateway),
        remediator=NoOpRemediator(),
        model_adapter=None,
        context_manager=DefaultContextManager(),
        tool_gateway=tool_gateway,
        security_boundary=DefaultSecurityBoundary(),
        execution_control=FileExecutionControl(event_log=event_log, checkpoint_dir=str(tmp_path / "checkpoints")),
        resource_manager=InMemoryResourceManager(default_budget=Budget(max_tool_calls=20, max_time_seconds=5)),
        event_log=event_log,
        extension_point=DefaultExtensionPoint(),
        run_context_state=run_context,
    )

    envelope = Envelope(
        allowed_capability_ids=["tool:noop"],
        budget=Budget(max_tool_calls=2),
        done_predicate=DonePredicate(
            evidence_conditions=[EvidenceCondition(condition_type="evidence_kind", params={"kind": "missing"})]
        ),
    )
    result = await orchestrator.run_tool_loop(ToolLoopRequest(capability_id="tool:noop", params={}, envelope=envelope))
    assert result.success is False
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_event_log_replay_returns_window(tmp_path):
    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))
    first_id = await event_log.append("test.start", {"value": 1})
    await event_log.append("test.next", {"value": 2})

    snapshot = await event_log.replay(from_event_id=first_id)
    assert snapshot.from_event_id == first_id
    assert len(snapshot.events) == 2
    assert snapshot.events[0].event_type == "test.start"


@pytest.mark.asyncio
async def test_tool_requires_approval_triggers_checkpoint_events(tmp_path):
    class ApprovalTool(ITool):
        @property
        def name(self) -> str:
            return "approval_tool"

        @property
        def description(self) -> str:
            return "tool that requires approval"

        @property
        def input_schema(self) -> dict[str, Any]:
            return {"type": "object", "properties": {}}

        @property
        def output_schema(self) -> dict[str, Any]:
            return {"type": "object", "properties": {"status": {"type": "string"}}}

        @property
        def tool_type(self) -> ToolType:
            return ToolType.ATOMIC

        @property
        def risk_level(self) -> RiskLevel:
            return RiskLevel.READ_ONLY

        @property
        def requires_approval(self) -> bool:
            return True

        @property
        def timeout_seconds(self) -> int:
            return 5

        @property
        def produces_assertions(self) -> list[dict[str, Any]]:
            return []

        @property
        def is_work_unit(self) -> bool:
            return False

        async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
            return ToolResult(success=True, output={"status": "ok"}, evidence=[])

    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))
    run_context = RunContext()

    tools = [ApprovalTool()]
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(NativeToolProvider(tools=tools, context_factory=lambda: run_context))

    orchestrator = DefaultLoopOrchestrator(
        planner=DeterministicPlanner([]),
        validator=GatewayValidator(tool_gateway),
        remediator=NoOpRemediator(),
        model_adapter=None,
        context_manager=DefaultContextManager(),
        tool_gateway=tool_gateway,
        security_boundary=DefaultSecurityBoundary(),
        execution_control=FileExecutionControl(event_log=event_log, checkpoint_dir=str(tmp_path / "checkpoints")),
        resource_manager=InMemoryResourceManager(default_budget=Budget(max_tool_calls=20, max_time_seconds=5)),
        event_log=event_log,
        extension_point=DefaultExtensionPoint(),
        run_context_state=run_context,
    )

    envelope = Envelope(allowed_capability_ids=["tool:approval_tool"])
    result = await orchestrator.run_tool_loop(
        ToolLoopRequest(capability_id="tool:approval_tool", params={}, envelope=envelope)
    )
    assert result.success is True

    pause_events = await event_log.query(filter={"event_type": "exec.pause"})
    waiting_events = await event_log.query(filter={"event_type": "exec.waiting_human"})
    resume_events = await event_log.query(filter={"event_type": "exec.resume"})
    checkpoint_events = await event_log.query(filter={"event_type": "exec.checkpoint"})
    assert len(pause_events) == 1
    assert len(waiting_events) == 1
    assert len(resume_events) == 1
    assert len(checkpoint_events) == 1


@pytest.mark.asyncio
async def test_execute_plan_requires_approval_triggers_waiting_events(tmp_path):
    class PlanApprovalBoundary(DefaultSecurityBoundary):
        async def check_policy(self, *, action: str, resource: str, context: dict[str, Any]) -> PolicyDecision:
            if action == "execute_plan":
                return PolicyDecision.APPROVE_REQUIRED
            return PolicyDecision.ALLOW

    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))
    run_context = RunContext()

    tools = [NoOpTool()]
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(NativeToolProvider(tools=tools, context_factory=lambda: run_context))

    planner = DeterministicPlanner(
        [
            [
                ProposedStep(step_id=generator_id("step"), capability_id="tool:noop", params={}),
            ]
        ]
    )
    validator = GatewayValidator(tool_gateway)

    orchestrator = DefaultLoopOrchestrator(
        planner=planner,
        validator=validator,
        remediator=NoOpRemediator(),
        model_adapter=None,
        context_manager=DefaultContextManager(),
        tool_gateway=tool_gateway,
        security_boundary=PlanApprovalBoundary(),
        execution_control=FileExecutionControl(event_log=event_log, checkpoint_dir=str(tmp_path / "checkpoints")),
        resource_manager=InMemoryResourceManager(default_budget=Budget(max_tool_calls=20, max_time_seconds=5)),
        event_log=event_log,
        extension_point=DefaultExtensionPoint(),
        run_context_state=run_context,
    )
    run_loop = DefaultRunLoop(orchestrator)

    result = await run_loop.run(Task(description="noop"))
    assert result.success is True

    pause_events = await event_log.query(filter={"event_type": "exec.pause"})
    waiting_events = await event_log.query(filter={"event_type": "exec.waiting_human"})
    resume_events = await event_log.query(filter={"event_type": "exec.resume"})
    assert len(pause_events) == 1
    assert len(waiting_events) == 1
    assert len(resume_events) == 1
