from __future__ import annotations

import pytest

from dare_framework.plan_v2.planner import Planner
from dare_framework.plan_v2.registry import SubAgentRegistry
from dare_framework.plan_v2.tools import (
    CreatePlanTool,
    FinishPlanTool,
    ReviseCurrentPlanTool,
    SubAgentTool,
    ValidatePlanTool,
)
from dare_framework.plan_v2.types import PlannerState, Step, is_valid_state_transition
from dare_framework.tool.types import RunContext


def _run_context() -> RunContext[None]:
    return RunContext()


@pytest.mark.asyncio
async def test_planner_exposes_revise_and_finish_plan_tools() -> None:
    planner = Planner(state=PlannerState())
    tool_names = {tool.name for tool in planner.list_tools()}
    assert "revise_current_plan" in tool_names
    assert "finish_plan" in tool_names


def test_plan_state_transition_rules_reject_terminal_reopen() -> None:
    assert is_valid_state_transition("todo", "in_progress") is True
    assert is_valid_state_transition("in_progress", "done") is True
    assert is_valid_state_transition("done", "in_progress") is False
    assert is_valid_state_transition("abandoned", "todo") is False


def test_sync_completed_step_ids_tolerates_legacy_steps_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str) -> None:
            self.step_id = step_id

    state = PlannerState(
        steps=[
            Step(step_id="s1", description="done step", status="done"),
            _LegacyStep(step_id="s_legacy"),
            {"step_id": "s_dict", "status": "done"},
        ]
    )

    state.sync_completed_step_ids()

    assert state.completed_step_ids == {"s1", "s_dict"}


def test_sync_completed_step_ids_preserves_legacy_completed_markers_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str) -> None:
            self.step_id = step_id

    state = PlannerState(steps=[_LegacyStep(step_id="legacy_done")])
    state.completed_step_ids = {"legacy_done"}

    state.sync_completed_step_ids()

    assert state.completed_step_ids == {"legacy_done"}


def test_transition_step_tolerates_legacy_step_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    state = PlannerState(steps=[_LegacyStep(step_id="s_legacy", description="legacy step")])

    state.transition_step("s_legacy", "in_progress")

    assert getattr(state.steps[0], "status") == "in_progress"


@pytest.mark.asyncio
async def test_finish_plan_rejects_done_when_pending_steps_exist() -> None:
    state = PlannerState()
    create_tool = CreatePlanTool(state)
    validate_tool = ValidatePlanTool(state)
    finish_tool = FinishPlanTool(state)

    await create_tool.execute(
        run_context=_run_context(),
        plan_description="d7-finish-guard",
        steps=[
            {"step_id": "s1", "description": "first"},
            {"step_id": "s2", "description": "second"},
        ],
    )
    await validate_tool.execute(run_context=_run_context(), success=True)

    result = await finish_tool.execute(run_context=_run_context(), target_state="done")

    assert result.success is False
    assert state.plan_status != "done"
    assert isinstance(result.error, str)
    assert "pending" in result.error.lower()


@pytest.mark.asyncio
async def test_finish_plan_done_honors_legacy_completed_markers_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    state = PlannerState(
        plan_description="legacy-plan",
        steps=[_LegacyStep(step_id="s1", description="legacy done step")],
        plan_status="in_progress",
        plan_validated=True,
    )
    state.completed_step_ids = {"s1"}
    finish_tool = FinishPlanTool(state)

    result = await finish_tool.execute(run_context=_run_context(), target_state="done")

    assert result.success is True
    assert state.plan_status == "done"
    assert result.output is not None
    assert result.output.get("pending") == []


@pytest.mark.asyncio
async def test_finish_plan_done_allows_restored_todo_plan_with_no_pending_steps() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    state = PlannerState(
        plan_description="legacy-restored-plan",
        steps=[_LegacyStep(step_id="s1", description="legacy done step")],
        plan_status="todo",
        plan_validated=True,
    )
    state.completed_step_ids = {"s1"}
    finish_tool = FinishPlanTool(state)

    result = await finish_tool.execute(run_context=_run_context(), target_state="done")

    assert result.success is True
    assert state.plan_status == "done"


@pytest.mark.asyncio
async def test_revise_current_plan_preserves_done_steps_by_step_id() -> None:
    state = PlannerState()
    create_tool = CreatePlanTool(state)
    validate_tool = ValidatePlanTool(state)
    revise_tool = ReviseCurrentPlanTool(state)

    await create_tool.execute(
        run_context=_run_context(),
        plan_description="initial",
        steps=[
            {"step_id": "s1", "description": "first"},
            {"step_id": "s2", "description": "second"},
        ],
    )
    await validate_tool.execute(run_context=_run_context(), success=True)
    state.steps[0].status = "done"
    state.completed_step_ids.add("s1")

    result = await revise_tool.execute(
        run_context=_run_context(),
        plan_description="revised",
        steps=[
            {"step_id": "s1", "description": "first revised"},
            {"step_id": "s3", "description": "third"},
        ],
    )

    assert result.success is True
    assert state.plan_description == "revised"
    assert [step.step_id for step in state.steps] == ["s1", "s3"]
    assert state.steps[0].status == "done"
    assert state.steps[1].status == "todo"


@pytest.mark.asyncio
async def test_revise_current_plan_handles_dict_backed_steps() -> None:
    state = PlannerState(
        plan_description="initial",
        steps=[
            {"step_id": "s1", "description": "first", "status": "done"},
            {"step_id": "s2", "description": "second", "status": "todo"},
        ],
        plan_status="in_progress",
    )
    state.completed_step_ids = {"s1"}
    revise_tool = ReviseCurrentPlanTool(state)

    result = await revise_tool.execute(
        run_context=_run_context(),
        steps=[
            {"step_id": "s1", "description": "first revised"},
            {"step_id": "s3", "description": "third"},
        ],
    )

    assert result.success is True
    assert [step.step_id for step in state.steps] == ["s1", "s3"]
    assert state.steps[0].status == "done"
    assert state.steps[1].status == "todo"


@pytest.mark.asyncio
async def test_revise_current_plan_preserves_legacy_completed_markers_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    state = PlannerState(
        plan_description="legacy-revise",
        steps=[_LegacyStep(step_id="s1", description="legacy done step")],
        plan_status="in_progress",
    )
    state.completed_step_ids = {"s1"}
    revise_tool = ReviseCurrentPlanTool(state)

    result = await revise_tool.execute(
        run_context=_run_context(),
        steps=[{"step_id": "s1", "description": "legacy done step revised"}],
    )

    assert result.success is True
    assert len(state.steps) == 1
    assert state.steps[0].status == "done"
    assert state.completed_step_ids == {"s1"}


@pytest.mark.asyncio
async def test_finish_plan_handles_dict_backed_steps() -> None:
    state = PlannerState(
        plan_description="dict-backed",
        steps=[
            {"step_id": "s1", "description": "first", "status": "done"},
            {"step_id": "s2", "description": "second", "status": "todo"},
        ],
        plan_status="in_progress",
        plan_validated=True,
    )
    finish_tool = FinishPlanTool(state)

    result = await finish_tool.execute(
        run_context=_run_context(),
        target_state="abandoned",
    )

    assert result.success is True
    assert state.plan_status == "abandoned"
    assert result.output is not None
    assert result.output.get("pending") == []


@pytest.mark.asyncio
async def test_finish_plan_abandoned_preserves_legacy_completed_markers_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    state = PlannerState(
        plan_description="legacy-abandoned",
        steps=[_LegacyStep(step_id="s1", description="legacy done step")],
        plan_status="in_progress",
        plan_validated=True,
    )
    state.completed_step_ids = {"s1"}
    finish_tool = FinishPlanTool(state)

    result = await finish_tool.execute(
        run_context=_run_context(),
        target_state="abandoned",
    )

    assert result.success is True
    assert state.plan_status == "abandoned"
    assert state.completed_step_ids == {"s1"}
    assert result.output is not None
    assert result.output.get("completed") == ["s1"]


@pytest.mark.asyncio
async def test_critical_block_requires_finish_when_all_steps_done() -> None:
    state = PlannerState()
    create_tool = CreatePlanTool(state)
    validate_tool = ValidatePlanTool(state)

    await create_tool.execute(
        run_context=_run_context(),
        plan_description="critical-block-finish",
        steps=[{"step_id": "s1", "description": "only step"}],
    )
    await validate_tool.execute(run_context=_run_context(), success=True)

    state.steps[0].status = "done"
    state.completed_step_ids.add("s1")
    await validate_tool.execute(run_context=_run_context(), success=True)

    assert "finish_plan" in state.critical_block


@pytest.mark.asyncio
async def test_critical_block_honors_legacy_completed_markers_without_status() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    state = PlannerState(
        plan_description="legacy-critical-block",
        steps=[_LegacyStep(step_id="s1", description="legacy done step")],
        plan_status="in_progress",
        plan_validated=True,
    )
    state.completed_step_ids = {"s1"}
    validate_tool = ValidatePlanTool(state)

    await validate_tool.execute(run_context=_run_context(), success=True)

    assert "- Completed: ['s1']" in state.critical_block
    assert "- Pending: []" in state.critical_block
    assert "finish_plan" in state.critical_block


@pytest.mark.asyncio
async def test_critical_block_does_not_suggest_finish_when_pending_step_id_is_invalid() -> None:
    state = PlannerState(
        plan_description="invalid-step-id",
        steps=[Step(step_id="   ", description="unnamed pending step", status="todo")],
        plan_status="in_progress",
        plan_validated=True,
    )
    validate_tool = ValidatePlanTool(state)

    result = await validate_tool.execute(run_context=_run_context(), success=True)

    assert result.success is True
    assert "- Pending: ['<unknown:1>']" in state.critical_block
    assert "finish_plan" not in state.critical_block
    assert "ask_user" in state.critical_block


@pytest.mark.asyncio
async def test_sub_agent_tool_blocks_legacy_completed_step_delegation() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    class _DummyAgent:
        calls = 0

        async def run(self, message: str, **kwargs: object) -> str:
            _ = message
            _ = kwargs
            type(self).calls += 1
            return "ok"

    state = PlannerState(
        plan_description="legacy-sub-agent",
        steps=[_LegacyStep(step_id="s1", description="already done in legacy session")],
        plan_status="in_progress",
        plan_validated=True,
    )
    state.completed_step_ids = {"s1"}
    registry = SubAgentRegistry()
    registry.register("worker", "test worker", _DummyAgent)
    tool = SubAgentTool(registry, "worker", state)

    result = await tool.execute(
        run_context=_run_context(),
        task="should not execute",
        step_id="s1",
    )

    assert result.success is False
    assert isinstance(result.error, str)
    assert "terminal" in result.error
    assert _DummyAgent.calls == 0


@pytest.mark.asyncio
async def test_sub_agent_tool_progress_excludes_legacy_completed_steps_from_pending() -> None:
    class _LegacyStep:
        def __init__(self, step_id: str, description: str) -> None:
            self.step_id = step_id
            self.description = description
            self.params = {}

    class _DummyAgent:
        async def run(self, message: str, **kwargs: object) -> dict[str, str]:
            _ = message
            _ = kwargs
            return {"ok": "true"}

    state = PlannerState(
        plan_description="legacy-progress",
        steps=[
            _LegacyStep(step_id="s1", description="legacy done"),
            Step(step_id="s2", description="active step"),
        ],
        plan_status="in_progress",
        plan_validated=True,
    )
    state.completed_step_ids = {"s1"}
    registry = SubAgentRegistry()
    registry.register("worker", "test worker", _DummyAgent)
    tool = SubAgentTool(registry, "worker", state)

    result = await tool.execute(
        run_context=_run_context(),
        task="execute active step",
        step_id="s2",
    )

    assert result.success is True
    assert isinstance(result.output, dict)
    progress = result.output.get("progress")
    assert isinstance(progress, str)
    assert "Completed: ['s1', 's2']" in progress
    assert "Pending: []" in progress


@pytest.mark.asyncio
async def test_finish_plan_done_rejects_pending_step_without_valid_id() -> None:
    state = PlannerState(
        plan_description="finish-guard-invalid-id",
        steps=[Step(step_id="   ", description="unnamed pending step", status="todo")],
        plan_status="in_progress",
        plan_validated=True,
    )
    finish_tool = FinishPlanTool(state)

    result = await finish_tool.execute(run_context=_run_context(), target_state="done")

    assert result.success is False
    assert state.plan_status != "done"
    assert isinstance(result.error, str)
    assert "pending steps exist" in result.error
