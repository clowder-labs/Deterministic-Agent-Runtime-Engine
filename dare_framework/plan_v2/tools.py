"""Plan tools: read/write PlannerState. Used by Plan Agent when Planner is mounted as IToolProvider."""

from __future__ import annotations

from typing import Any

from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)

from dare_framework.plan_v2.registry import SubAgentRegistry
from dare_framework.plan_v2.types import Milestone, PlannerState, Step


def _format_critical_block(state: PlannerState) -> str:
    """Format plan state for the critical block. Tools call this after mutating state."""
    if not state.steps:
        return (
            "## [Plan State]\n\n"
            "- Phase: no_plan\n"
            "- **NEXT**: Call create_plan with plan_description and steps."
        )
    completed = sorted(state.completed_step_ids)
    pending = [s.step_id for s in state.steps if s.step_id not in state.completed_step_ids]
    lines = [
        "## [Plan State] (check before every action)",
        "",
        f"- Plan: {state.plan_description}",
        "- Steps:",
    ]
    for i, st in enumerate(state.steps, 1):
        lines.append(f"  [{i}] {st.step_id}: {st.description}")
    lines.extend(["", f"- Completed: {completed}", f"- Pending: {pending}"])
    if not state.plan_validated:
        lines.append("- **NEXT**: Call validate_plan(success=True) to confirm the plan.")
    elif pending:
        next_step = next(s for s in state.steps if s.step_id == pending[0])
        lines.append(
            f"- **NEXT**: Call sub-agent (e.g. sub_agent_general) with task=<{next_step.step_id} description> "
            f"and step_id={next_step.step_id}. Do NOT repeat completed steps."
        )
    else:
        lines.append("- **NEXT**: All steps completed. Summarize results and report to user.")
    return "\n".join(lines)


class CreatePlanTool(ITool):
    """Create or replace the current plan (description + steps) for the current milestone/task."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return (
            "Create the plan once. Call only when no plan exists yet. Provide plan_description and a list of steps. "
            "Each step has step_id, description, and optional params. After success, proceed to validate_plan."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        plan_description: str,
        steps: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Write plan to PlannerState.

        Args:
            run_context: Runtime context.
            plan_description: Short description of the plan.
            steps: List of {"step_id": str, "description": str, "params": dict}.
        """
        # 已有 plan 时拒绝覆盖，引导模型进入 validate/execute 阶段
        if self._state.steps:
            self._state.critical_block = _format_critical_block(self._state)
            print("\n--- Plan Already Exists (skipping overwrite) ---")
            print(f"  steps: {len(self._state.steps)}")
            print("---\n", flush=True)
            return ToolResult(
                success=True,
                output={
                    "skipped": True,
                    "reason": "Plan already exists.",
                    "next_action": "Do NOT call create_plan again. Call validate_plan(success=True), then delegate each step exactly once to the matching sub-agent (e.g. sub_agent_general) with task=<step description>.",
                },
            )
        self._state.plan_description = plan_description
        self._state.steps = [
            Step(
                step_id=s.get("step_id", ""),
                description=s.get("description", ""),
                params=s.get("params") or {},
            )
            for s in steps
        ]
        self._state.completed_step_ids.clear()
        self._state.critical_block = _format_critical_block(self._state)
        print("\n--- Plan Created ---")
        print(f"  plan_description: {plan_description}")
        print(f"  steps ({len(self._state.steps)}):")
        for i, st in enumerate(self._state.steps, 1):
            print(f"    [{i}] {st.step_id}: {st.description}")
        print("---\n", flush=True)
        return ToolResult(
            success=True,
            output={
                "plan_description": plan_description,
                "steps_count": len(self._state.steps),
                "next_action": "Now call validate_plan(success=True) to confirm, then delegate each step exactly once to sub-agents.",
            },
        )


class ValidatePlanTool(ITool):
    """Mark the current plan as validated or record validation errors (e.g. from external validator)."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "validate_plan"

    @property
    def description(self) -> str:
        return "Set plan validation result: success and optional list of error messages."

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        success: bool = True,
        errors: list[str] | None = None,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Write validation result to PlannerState."""
        self._state.plan_success = success
        self._state.plan_errors = list(errors or [])
        if success:
            self._state.plan_validated = True
        self._state.critical_block = _format_critical_block(self._state)
        return ToolResult(success=True, output={"plan_success": success, "errors": self._state.plan_errors})


class VerifyMilestoneTool(ITool):
    """Record milestone verification result (errors if not met)."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "verify_milestone"

    @property
    def description(self) -> str:
        return "Set milestone verification result: list of error messages if not met, empty if success."

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        errors: list[str] | None = None,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Write verify result to PlannerState."""
        self._state.last_verify_errors = list(errors or [])
        return ToolResult(success=True, output={"verify_errors": self._state.last_verify_errors})


class ReflectTool(ITool):
    """Record remediation/reflection summary for the current milestone."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "reflect"

    @property
    def description(self) -> str:
        return "Record a short remediation or reflection summary (e.g. after verification failure)."

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        summary: str,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Write remediation summary to PlannerState."""
        self._state.last_remediation_summary = summary
        return ToolResult(success=True, output={"remediation_summary": summary})


class DecomposeTaskTool(ITool):
    """Decompose task into milestones and optionally set current milestone."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "decompose_task"

    @property
    def description(self) -> str:
        return (
            "Set the list of milestones for the current task. Each milestone has "
            "milestone_id, description, success_criteria (list), optional metadata."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        milestones: list[dict[str, Any]],
        current_milestone_id: str | None = None,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Write milestones to PlannerState and optionally set current_milestone_id."""
        self._state.milestones = [
            Milestone(
                milestone_id=m.get("milestone_id", ""),
                description=m.get("description", ""),
                success_criteria=m.get("success_criteria") or [],
                metadata=m.get("metadata") or {},
            )
            for m in milestones
        ]
        if current_milestone_id is not None:
            self._state.current_milestone_id = current_milestone_id
        elif self._state.milestones and not self._state.current_milestone_id:
            self._state.current_milestone_id = self._state.milestones[0].milestone_id
        return ToolResult(
            success=True,
            output={"milestones_count": len(self._state.milestones), "current_milestone_id": self._state.current_milestone_id},
        )


class DelegateToSubAgentTool(ITool):
    """Placeholder: delegate a sub-task to another agent (orchestrator uses this)."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "delegate_to_sub_agent"

    @property
    def description(self) -> str:
        return "Request delegation of a sub-task to another agent. Used by meta-planner; implementation is orchestrator-specific."

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 5

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.PLAN_TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        sub_task_description: str,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Stub: actual delegation is done by orchestrator."""
        return ToolResult(
            success=True,
            output={"delegated": sub_task_description, "note": "Orchestrator should handle delegation."},
        )


class SubAgentTool(ITool):
    """Invoke a registered sub-agent with a task (e.g. one step). Plan Agent uses this to delegate; instantiate on call."""

    def __init__(
        self,
        registry: SubAgentRegistry,
        sub_agent_id: str,
        state: PlannerState | None = None,
    ) -> None:
        self._registry = registry
        self._sub_agent_id = sub_agent_id
        self._state = state

    @property
    def name(self) -> str:
        return self._sub_agent_id

    @property
    def description(self) -> str:
        return self._registry.get_description(self._sub_agent_id)

    @property
    def input_schema(self) -> dict[str, Any]:
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return infer_output_schema_from_execute(type(self).execute)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 120

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.AGENT

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        task: str,
        step_id: str | None = None,
        **kwargs: Any,
    ) -> ToolResult[Any]:
        """Run the sub-agent with the given task (e.g. step description). Returns the sub-agent result.
        When step_id is provided and call succeeds, marks that step as completed and adds progress to output."""
        task_preview = (task[:120] + "...") if len(task) > 120 else task
        print(f"\n>>> 委托 {self._sub_agent_id}: {task_preview}\n", flush=True)
        try:
            result = await self._registry.run(self._sub_agent_id, task, **kwargs)
            if step_id and self._state:
                self._state.completed_step_ids.add(step_id)
                self._state.critical_block = _format_critical_block(self._state)
            print(f"<<< {self._sub_agent_id} 返回 (success=True)\n", flush=True)
            output = result
            if self._state and self._state.steps:
                completed = sorted(self._state.completed_step_ids)
                pending = [
                    s.step_id
                    for s in self._state.steps
                    if s.step_id not in self._state.completed_step_ids
                ]
                progress = f"Completed: {completed}. Pending: {pending}."
                if isinstance(result, dict):
                    output = {**result, "progress": progress}
                else:
                    output = {"result": result, "progress": progress}
            return ToolResult(success=True, output=output)
        except Exception as exc:
            print(f"<<< {self._sub_agent_id} 返回 (error: {exc})\n", flush=True)
            return ToolResult(success=False, output=None, error=str(exc))


__all__ = [
    "CreatePlanTool",
    "DecomposeTaskTool",
    "DelegateToSubAgentTool",
    "ReflectTool",
    "SubAgentTool",
    "ValidatePlanTool",
    "VerifyMilestoneTool",
]
