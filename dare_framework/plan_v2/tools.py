"""Plan tools: read/write PlannerState. Used by Plan Agent when Planner is mounted as IToolProvider."""

from __future__ import annotations

from typing import Any

# sub-agent 相关日志用绿字
_ANSI_GREEN = "\033[32m"
_ANSI_RESET = "\033[0m"

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
from dare_framework.plan_v2.types import (
    Milestone,
    PlanStateName,
    PlannerState,
    STEP_STATES,
    Step,
)

_TERMINAL_STATES: set[str] = {"done", "abandoned"}
_PENDING_STATES: set[str] = {"todo", "in_progress"}


def _step_id(step: Any) -> str | None:
    """Read step_id from Step-like objects with legacy dict fallback."""
    raw = getattr(step, "step_id", None)
    if raw is None and isinstance(step, dict):
        raw = step.get("step_id")
    if isinstance(raw, str) and raw.strip():
        return raw
    return None


def _step_description(step: Any) -> str:
    """Read step description from Step-like objects with legacy dict fallback."""
    raw = getattr(step, "description", None)
    if raw is None and isinstance(step, dict):
        raw = step.get("description")
    return str(raw or "")


def _step_state(step: Any) -> PlanStateName:
    """Read a step lifecycle state with fallback for legacy objects."""
    raw = getattr(step, "status", None)
    if raw is None and isinstance(step, dict):
        raw = step.get("status")
    if isinstance(raw, str) and raw in STEP_STATES:
        return raw
    return "todo"


def _step_has_explicit_status(step: Any) -> bool:
    """Return True when status is explicitly stored on the step object."""
    if isinstance(step, dict):
        return "status" in step
    return hasattr(step, "status")


def _set_step_state(step: Any, status: PlanStateName) -> None:
    """Set step status for object/dict-backed step entries."""
    if isinstance(step, dict):
        step["status"] = status
        return
    setattr(step, "status", status)


def _is_step_completed(state: PlannerState, step: Any) -> bool:
    """Return whether a step should be treated as completed, including legacy markers."""
    if _step_state(step) == "done":
        return True
    step_id = _step_id(step)
    return (
        step_id is not None
        and step_id in state.completed_step_ids
        and not _step_has_explicit_status(step)
    )


def _pending_steps(state: PlannerState) -> list[Any]:
    """Return non-terminal steps, honoring legacy completed markers when status is absent."""
    pending: list[Any] = []
    for step in state.steps:
        if _step_state(step) not in _PENDING_STATES:
            continue
        if _is_step_completed(state, step):
            # Legacy restored sessions may store completion only in completed_step_ids.
            # Avoid reclassifying these steps as pending when status was never persisted.
            continue
        pending.append(step)
    return pending


def _format_critical_block(state: PlannerState) -> str:
    """Format plan state for the critical block. Tools call this after mutating state."""
    if not state.steps:
        return (
            "## [Plan State]\n\n"
            "- Phase: no_plan\n"
            "- **NEXT**: Call create_plan with plan_description and steps."
        )
    state.sync_completed_step_ids()
    pending_steps = _pending_steps(state)
    completed = [step_id for step in state.steps if _is_step_completed(state, step) if (step_id := _step_id(step))]
    pending = [(_step_id(step) or f"<unknown:{i + 1}>") for i, step in enumerate(pending_steps)]
    abandoned = [step_id for step in state.steps if _step_state(step) == "abandoned" if (step_id := _step_id(step))]
    lines = [
        "## [Plan State] (check before every action)",
        "",
        f"- Plan: {state.plan_description}",
        f"- Plan Status: {state.plan_status}",
        "- Steps:",
    ]
    for i, st in enumerate(state.steps, 1):
        lines.append(f"  [{i}] {_step_id(st) or '<unknown>'} [{_step_state(st)}]: {_step_description(st)}")
        params = st.params if isinstance(st, Step) else st.get("params", {}) if isinstance(st, dict) else {}
        if isinstance(params, dict) and params.get("deliverable"):
            lines.append(f"      交付件: {params['deliverable']}")
    lines.extend(["", f"- Completed: {completed}", f"- Pending: {pending}", f"- Abandoned: {abandoned}"])

    if state.plan_status in _TERMINAL_STATES:
        lines.append(f"- **NEXT**: Plan is terminal (`{state.plan_status}`). Report result and stop planning tools.")
        return "\n".join(lines)
    if not state.plan_validated:
        lines.append("- **NEXT**: Call validate_plan(success=True) to confirm the plan.")
    elif pending_steps and not completed:
        lines.append("- **NEXT**: Call ask_user to show the plan and ask for approval (执行/修改计划/取消). Only proceed to delegate when user chooses 执行.")
    elif pending_steps:
        next_step = pending_steps[0]
        next_step_id = _step_id(next_step)
        if not next_step_id:
            lines.append(
                "- **NEXT**: Call revise_current_plan to assign valid step_id values for pending steps "
                "before delegation or finish_plan."
            )
            return "\n".join(lines)
        params = next_step.params if isinstance(next_step, Step) else next_step.get("params", {}) if isinstance(next_step, dict) else {}
        deliverable = params.get("deliverable", "") if isinstance(params, dict) else ""
        dl_hint = f" 交付件: {deliverable}" if deliverable else ""
        lines.append(
            f"- **NEXT**: Call sub-agent with task=<任务目标 + 交付件 + 目标路径> and step_id={next_step_id}.{dl_hint} "
            f"Do NOT add execution steps to task. Do NOT fabricate file paths. Do NOT repeat completed steps."
        )
    else:
        target = "done" if not abandoned else "abandoned"
        lines.append(
            f"- **NEXT**: All steps are terminal. Call finish_plan(target_state=\"{target}\") to close this plan."
        )
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
            "Each step: step_id, description (任务目标，不写具体执行步骤), params.deliverable (绝对路径或自然语言). "
            "禁止在 step 中写「如何做」（如先读 A 再读 B、调用某工具等）。执行方式由 sub-agent 自主决定。After success, proceed to validate_plan."
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
                    "next_action": "Do NOT call create_plan again. Call validate_plan(success=True), then delegate each step exactly once with task=<任务目标 + 交付件 + 目标路径> (no execution steps).",
                },
            )
        seen_step_ids: set[str] = set()
        duplicate_step_ids: set[str] = set()
        for raw_step in steps:
            step_id = str(raw_step.get("step_id", "")).strip()
            if not step_id:
                continue
            if step_id in seen_step_ids:
                duplicate_step_ids.add(step_id)
            seen_step_ids.add(step_id)
        if duplicate_step_ids:
            duplicates = sorted(duplicate_step_ids)
            return ToolResult(
                success=False,
                output=None,
                error=f"duplicate step_id values are not allowed: {duplicates}",
            )
        self._state.plan_description = plan_description
        self._state.steps = [
            Step(
                step_id=str(s.get("step_id", "")).strip(),
                description=s.get("description", ""),
                params=s.get("params") or {},
                status="todo",
            )
            for s in steps
        ]
        self._state.plan_status = "todo"
        self._state.completed_step_ids.clear()
        self._state.plan_validated = False
        self._state.critical_block = _format_critical_block(self._state)
        print("\n--- Plan Created ---")
        print(f"  plan_description: {plan_description}")
        print(f"  steps ({len(self._state.steps)}):")
        for i, st in enumerate(self._state.steps, 1):
            params = st.params if isinstance(st, Step) else st.get("params", {}) if isinstance(st, dict) else {}
            dl = params.get("deliverable", "") if isinstance(params, dict) else ""
            dl_str = f" 交付件: {dl}" if dl else ""
            print(f"    [{i}] {_step_id(st) or '<unknown>'}: {_step_description(st)}{dl_str}")
        print("---\n", flush=True)
        return ToolResult(
            success=True,
            output={
                "plan_description": plan_description,
                "steps_count": len(self._state.steps),
                "next_action": "Now call validate_plan(success=True) to confirm, then delegate each step with task=<任务目标 + 交付件 + 目标路径> (no execution steps).",
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
            if self._state.plan_status == "todo":
                self._state.plan_status = "in_progress"
        else:
            self._state.plan_validated = False
        self._state.critical_block = _format_critical_block(self._state)
        return ToolResult(
            success=True,
            output={
                "plan_success": success,
                "plan_status": self._state.plan_status,
                "errors": self._state.plan_errors,
            },
        )


class ReviseCurrentPlanTool(ITool):
    """Revise the current plan definition while keeping stable completed progress by step_id."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "revise_current_plan"

    @property
    def description(self) -> str:
        return (
            "Revise current plan_description and/or steps. "
            "Terminal plans (done/abandoned) cannot be revised."
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
        plan_description: str | None = None,
        steps: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Revise current plan and reset validation gate."""
        _ = run_context
        if not self._state.steps:
            return ToolResult(success=False, output=None, error="no active plan to revise")
        if self._state.plan_status in _TERMINAL_STATES:
            return ToolResult(
                success=False,
                output=None,
                error=f"cannot revise terminal plan ({self._state.plan_status})",
            )
        if plan_description is None and steps is None:
            return ToolResult(success=False, output=None, error="no revision payload provided")

        if steps is not None:
            seen_step_ids: set[str] = set()
            duplicate_step_ids: set[str] = set()
            for raw_step in steps:
                step_id = str(raw_step.get("step_id", "")).strip()
                if not step_id:
                    continue
                if step_id in seen_step_ids:
                    duplicate_step_ids.add(step_id)
                seen_step_ids.add(step_id)
            if duplicate_step_ids:
                duplicates = sorted(duplicate_step_ids)
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"duplicate step_id values are not allowed: {duplicates}",
                )
            old_by_id = {
                step_id: ("done" if _is_step_completed(self._state, step) else _step_state(step))
                for step in self._state.steps
                if (step_id := _step_id(step)) is not None
            }
            revised_steps: list[Step] = []
            for raw in steps:
                step_id = str(raw.get("step_id", "")).strip()
                if not step_id:
                    continue
                preserved = old_by_id.get(step_id, "todo")
                status: PlanStateName = preserved if preserved in _TERMINAL_STATES else "todo"
                revised_steps.append(
                    Step(
                        step_id=step_id,
                        description=str(raw.get("description", "")),
                        params=raw.get("params") or {},
                        status=status,
                    )
                )
            self._state.steps = revised_steps
            self._state.sync_completed_step_ids()

        if plan_description is not None:
            self._state.plan_description = str(plan_description)

        self._state.plan_validated = False
        self._state.plan_status = "todo"
        self._state.critical_block = _format_critical_block(self._state)
        return ToolResult(
            success=True,
            output={
                "plan_description": self._state.plan_description,
                "steps_count": len(self._state.steps),
                "next_action": "Call validate_plan(success=True) after revision.",
            },
        )


class FinishPlanTool(ITool):
    """Explicitly mark plan as done/abandoned with state guardrails."""

    def __init__(self, state: PlannerState) -> None:
        self._state = state

    @property
    def name(self) -> str:
        return "finish_plan"

    @property
    def description(self) -> str:
        return "Mark current plan terminal with target_state in {'done','abandoned'}."

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
        return 20

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
        target_state: str = "done",
        summary: str | None = None,
        **kwargs: Any,
    ) -> ToolResult[dict[str, Any]]:
        """Finish the plan with deterministic terminal-state rules."""
        _ = run_context
        if target_state not in _TERMINAL_STATES:
            return ToolResult(
                success=False,
                output=None,
                error=f"invalid target_state: {target_state}",
            )
        if not self._state.steps:
            return ToolResult(success=False, output=None, error="no active plan to finish")

        pending_steps = _pending_steps(self._state)
        pending = [(_step_id(step) or f"<unknown:{i + 1}>") for i, step in enumerate(pending_steps)]
        if target_state == "done" and pending_steps:
            return ToolResult(
                success=False,
                output=None,
                error=f"pending steps exist: {pending}",
            )

        try:
            self._state.transition_plan(target_state)
        except ValueError as exc:
            return ToolResult(success=False, output=None, error=str(exc))

        if target_state == "abandoned":
            for step in pending_steps:
                step_id = _step_id(step)
                if step_id:
                    self._state.transition_step(step_id, "abandoned")
                else:
                    _set_step_state(step, "abandoned")

        if summary:
            self._state.last_remediation_summary = str(summary)
        self._state.critical_block = _format_critical_block(self._state)
        return ToolResult(
            success=True,
            output={
                "plan_status": self._state.plan_status,
                "pending": [step_id for step in _pending_steps(self._state) if (step_id := _step_id(step))],
                "completed": sorted(self._state.completed_step_ids),
            },
        )


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
        _ = run_context
        if self._state and self._state.plan_status in _TERMINAL_STATES:
            return ToolResult(
                success=False,
                output=None,
                error=f"plan already terminal: {self._state.plan_status}",
            )
        task_preview = (task[:600] + "...") if len(task) > 600 else task
        print(f"{_ANSI_GREEN}\n>>> 委托 {self._sub_agent_id}: {task_preview}\n{_ANSI_RESET}", flush=True)
        if step_id and self._state:
            step = self._state.get_step(step_id)
            if step is None:
                return ToolResult(success=False, output=None, error=f"unknown step_id: {step_id}")
            terminal_state = "done" if _is_step_completed(self._state, step) else _step_state(step)
            if terminal_state in _TERMINAL_STATES:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"step already terminal: {step_id} ({terminal_state})",
                )
            self._state.transition_step(step_id, "in_progress")
            if self._state.plan_status == "todo":
                self._state.plan_status = "in_progress"
            self._state.critical_block = _format_critical_block(self._state)
        try:
            result = await self._registry.run(self._sub_agent_id, task, **kwargs)
            if step_id and self._state:
                self._state.transition_step(step_id, "done")
                self._state.critical_block = _format_critical_block(self._state)
            print(f"{_ANSI_GREEN}<<< {self._sub_agent_id} 返回 (success=True)\n{_ANSI_RESET}", flush=True)
            output = result
            if self._state and self._state.steps:
                self._state.sync_completed_step_ids()
                completed = sorted(self._state.completed_step_ids)
                pending = [(_step_id(s) or f"<unknown:{i + 1}>") for i, s in enumerate(_pending_steps(self._state))]
                progress = f"Completed: {completed}. Pending: {pending}."
                if isinstance(result, dict):
                    output = {**result, "progress": progress}
                else:
                    output = {"result": result, "progress": progress}
            return ToolResult(success=True, output=output)
        except Exception as exc:
            if step_id and self._state:
                self._state.critical_block = _format_critical_block(self._state)
            print(f"{_ANSI_GREEN}<<< {self._sub_agent_id} 返回 (error: {exc})\n{_ANSI_RESET}", flush=True)
            return ToolResult(success=False, output=None, error=str(exc))


__all__ = [
    "CreatePlanTool",
    "DecomposeTaskTool",
    "DelegateToSubAgentTool",
    "FinishPlanTool",
    "ReflectTool",
    "ReviseCurrentPlanTool",
    "SubAgentTool",
    "ValidatePlanTool",
    "VerifyMilestoneTool",
]
