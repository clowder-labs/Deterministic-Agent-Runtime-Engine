from __future__ import annotations

import pytest

from dare_framework.plan_v2.planner import Planner
from dare_framework.plan_v2.tools import (
    CreatePlanTool,
    FinishPlanTool,
    ReviseCurrentPlanTool,
    ValidatePlanTool,
)
from dare_framework.plan_v2.types import PlannerState, is_valid_state_transition
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

