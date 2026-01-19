import pytest

from dare_framework.builder import AgentBuilder
from dare_framework.components.planners.deterministic import DeterministicPlanner
from dare_framework.components.tools.noop import NoOpTool
from dare_framework.contracts.ids import generator_id
from dare_framework.core.event.local_event_log import LocalEventLog
from dare_framework.core.plan.planning import ProposedStep


@pytest.mark.asyncio
async def test_builder_wires_kernel_defaults(tmp_path):
    event_log = LocalEventLog(path=str(tmp_path / "events.jsonl"))

    planner = DeterministicPlanner(
        [
            [
                ProposedStep(step_id=generator_id("step"), capability_id="tool:noop", params={}),
            ]
        ]
    )

    agent = (
        AgentBuilder("test")
        .with_kernel_defaults()
        .with_event_log(event_log)
        .with_checkpoint_dir(str(tmp_path / "checkpoints"))
        .with_tools(NoOpTool())
        .with_planner(planner)
        .build()
    )

    result = await agent.run("noop")
    assert result.success is True
    assert await event_log.verify_chain() is True
