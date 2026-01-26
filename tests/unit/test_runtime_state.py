import pytest

import pytest

pytest.skip(
    "Legacy runtime state tests are archived; port to canonical dare_framework once "
    "full runtime/orchestrator implementations exist.",
    allow_module_level=True,
)

from dare_framework.plan.impl.planners.deterministic import DeterministicPlanner
from dare_framework.tool.impl.providers.native_tool_provider import NativeToolProvider
from dare_framework.plan.impl.remediators.noop import NoOpRemediator
from dare_framework.tool.impl.tools.noop import NoOpTool
from dare_framework.plan.impl.validators.kernel_validator import GatewayValidator
from dare_framework.contracts.ids import generator_id
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
from dare_framework.tool.impl.run_context_state import RunContextState
from dare_framework.plan.planning import ProposedStep
from dare_framework.execution.types import RunLoopState
from dare_framework.plan.task import Task


@pytest.mark.asyncio
async def test_run_loop_transitions_to_completed(tmp_path):
    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))
    run_context = RunContextState()

    tools = [NoOpTool()]
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(NativeToolProvider(tools=tools, context_factory=run_context.build))

    planner = DeterministicPlanner(
        [
            [
                ProposedStep(step_id=generator_id("step"), capability_id="tool:noop", params={}),
            ]
        ]
    )
    validator = GatewayValidator(tool_gateway)
    remediator = NoOpRemediator()

    orchestrator = DefaultLoopOrchestrator(
        planner=planner,
        validator=validator,
        remediator=remediator,
        model_adapter=None,
        context_manager=DefaultContextManager(),
        tool_gateway=tool_gateway,
        security_boundary=DefaultSecurityBoundary(),
        execution_control=FileExecutionControl(event_log=event_log, checkpoint_dir=str(tmp_path / "checkpoints")),
        resource_manager=InMemoryResourceManager(default_budget=Budget(max_tool_calls=10, max_time_seconds=5)),
        event_log=event_log,
        extension_point=DefaultExtensionPoint(),
        run_context_state=run_context,
    )
    run_loop = DefaultRunLoop(orchestrator)

    task = Task(description="noop")
    result = await run_loop.run(task)

    assert result.success is True
    assert result.session_summary is not None
    assert result.session_summary.success is True
    assert result.milestone_results[0].summary is not None
    assert run_loop.state == RunLoopState.COMPLETED
