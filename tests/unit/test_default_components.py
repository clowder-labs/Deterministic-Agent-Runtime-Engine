import pytest

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
from dare_framework.core.events import Event, EventFilter
from dare_framework.core.models import Milestone, MilestoneContext, RunContext
from dare_framework.models import NoopModelAdapter
from dare_framework.tools import NoopTool
from dare_framework.validators import DefaultValidator


@pytest.mark.asyncio
async def test_in_memory_event_log_query_filters():
    event_log = InMemoryEventLog()
    await event_log.append(Event(event_type="alpha", payload={"milestone_id": "m1"}))
    await event_log.append(Event(event_type="beta", payload={"milestone_id": "m2"}))

    events = await event_log.query(EventFilter(event_types=["alpha"]))
    assert len(events) == 1
    assert events[0].event_type == "alpha"

    events = await event_log.query(EventFilter(milestone_id="m2"))
    assert len(events) == 1
    assert events[0].payload["milestone_id"] == "m2"


@pytest.mark.asyncio
async def test_in_memory_checkpoint_roundtrip():
    checkpoint = InMemoryCheckpoint()
    summary = await _sample_summary("m1")
    await checkpoint.save_milestone_summary("m1", summary)

    loaded = await checkpoint.load_milestone_summary("m1")
    assert loaded.milestone_id == "m1"
    assert await checkpoint.is_completed("m1") is True


@pytest.mark.asyncio
async def test_default_plan_generator_emits_step():
    generator = DefaultPlanGenerator(tool_name="noop")
    milestone = Milestone(milestone_id="m1", description="Do work", user_input="Do work")
    plan = await generator.generate_plan(milestone, MilestoneContext("u", "m"), [], RunContext(None, "r1"))
    assert plan.proposed_steps
    assert plan.proposed_steps[0].tool_name == "noop"


@pytest.mark.asyncio
async def test_default_validator_validates_registered_tool():
    toolkit = BasicToolkit()
    toolkit.register_tool(NoopTool())
    validator = DefaultValidator(toolkit=toolkit)

    milestone = Milestone(milestone_id="m1", description="Do work", user_input="Do work")
    plan = await DefaultPlanGenerator().generate_plan(
        milestone,
        MilestoneContext("u", "m"),
        [],
        RunContext(None, "r1"),
    )

    result = await validator.validate_plan(plan.proposed_steps, RunContext(None, "r1"))
    assert result.is_valid is True
    assert result.validated_steps[0].tool_name == "noop"


@pytest.mark.asyncio
async def test_tool_runtime_invokes_tool():
    toolkit = BasicToolkit()
    toolkit.register_tool(NoopTool())
    runtime = DefaultToolRuntime(toolkit, AllowAllPolicy())

    result = await runtime.invoke("noop", {"message": "hi"}, RunContext(None, "r1"))
    assert result.success is True
    assert "noop:hi" in result.output


@pytest.mark.asyncio
async def test_context_assembler_returns_reflections():
    assembler = DefaultContextAssembler()
    milestone = Milestone(milestone_id="m1", description="Do work", user_input="Do work")
    milestone_ctx = MilestoneContext("user", "Do work")
    milestone_ctx.reflections.append("note")

    context = await assembler.assemble(milestone, milestone_ctx, RunContext(None, "r1"))
    assert context.reflections == ["note"]
    assert context.milestone_description == "Do work"


@pytest.mark.asyncio
async def test_remediator_returns_reflection():
    remediator = DefaultRemediator()
    result = await remediator.remediate(
        verify_result=_sample_verify(False),
        tool_errors=[],
        milestone_ctx=MilestoneContext("u", "m"),
        ctx=RunContext(None, "r1"),
    )
    assert result


@pytest.mark.asyncio
async def test_noop_model_adapter_is_deterministic():
    model = NoopModelAdapter(response_text="ok")
    response = await model.generate(messages=[], tools=None)
    assert response.content == "ok"
    assert response.tool_calls == []


async def _sample_summary(milestone_id: str):
    from dare_framework.core.models import MilestoneSummary

    return MilestoneSummary(
        milestone_id=milestone_id,
        milestone_description="desc",
        deliverables=[],
        what_worked="",
        what_failed="",
        key_insight="",
        completeness=0.0,
        termination_reason="",
        attempts=0,
        duration_seconds=0.0,
    )


def _sample_verify(passed: bool):
    from dare_framework.core.models import QualityMetrics, VerifyResult

    return VerifyResult(
        passed=passed,
        completeness=1.0 if passed else 0.0,
        quality_metrics=QualityMetrics(),
        failure_reason=None if passed else "fail",
    )
