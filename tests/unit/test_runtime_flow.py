import pytest

from dare_framework import AgentRuntime
from dare_framework.components import (
    AllowAllPolicy,
    BasicToolkit,
    DefaultContextAssembler,
    DefaultPlanGenerator,
    DefaultRemediator,
    DefaultToolRuntime,
    InMemoryCheckpoint,
    InMemoryEventLog,
)
from dare_framework.core.models import Task
from dare_framework.models import NoopModelAdapter
from dare_framework.tools import NoopTool
from dare_framework.validators import DefaultValidator


@pytest.mark.asyncio
async def test_runtime_flow_completes_with_defaults():
    toolkit = BasicToolkit()
    toolkit.register_tool(NoopTool())

    runtime = AgentRuntime(
        event_log=InMemoryEventLog(),
        tool_runtime=DefaultToolRuntime(toolkit, AllowAllPolicy()),
        policy_engine=AllowAllPolicy(),
        plan_generator=DefaultPlanGenerator(),
        validator=DefaultValidator(toolkit=toolkit),
        remediator=DefaultRemediator(),
        context_assembler=DefaultContextAssembler(),
        model_adapter=NoopModelAdapter(response_text="done"),
        checkpoint=InMemoryCheckpoint(),
    )

    task = Task(description="Test runtime flow")
    await runtime.init(task)
    result = await runtime.run(task, deps=None)

    assert result.success is True
    assert result.session_summary is not None
    assert result.session_summary.milestone_count == 1
