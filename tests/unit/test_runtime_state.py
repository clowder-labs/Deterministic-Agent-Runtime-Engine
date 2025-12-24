import pytest

from dare_framework.checkpoint import FileCheckpoint
from dare_framework.defaults import DeterministicPlanGenerator, NoOpTool
from dare_framework.event_log import LocalEventLog
from dare_framework.models import PlanStep, RuntimeState, Task, new_id
from dare_framework.registries import SkillRegistry, ToolRegistry
from dare_framework.runtime import AgentRuntime
from dare_framework.tool_runtime import ToolRuntime
from dare_framework.defaults import AllowAllPolicyEngine, SimpleValidator


@pytest.mark.asyncio
async def test_runtime_transitions_to_stopped(tmp_path):
    plan_generator = DeterministicPlanGenerator(
        [[PlanStep(step_id=new_id("step"), tool_name="noop", tool_input={})]]
    )

    tool_registry = ToolRegistry()
    tool_registry.register_tool(NoOpTool())
    skill_registry = SkillRegistry()

    tool_runtime = ToolRuntime(
        toolkit=tool_registry,
        skill_registry=skill_registry,
        policy_engine=AllowAllPolicyEngine(),
        validator=SimpleValidator(),
    )

    runtime = AgentRuntime(
        tool_runtime=tool_runtime,
        plan_generator=plan_generator,
        event_log=LocalEventLog(path=str(tmp_path / "events.jsonl")),
        checkpoint=FileCheckpoint(path=str(tmp_path / "checkpoints")),
    )

    task = Task(description="noop")
    await runtime.init(task)
    result = await runtime.run(task, None)

    assert result.success is True
    assert result.session_summary is not None
    assert result.session_summary.success is True
    assert result.milestone_results[0].summary is not None
    assert runtime.get_state() == RuntimeState.STOPPED
