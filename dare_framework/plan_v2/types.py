"""plan_v2 types - self-contained, no dependency on dare_framework.plan.

Design principles (from discussion):
- Plan Agent and Execution Agent are separate; copy_for_execution() passes clean state.
- Step does NOT specify capability_id; executor decides which tools to use.
- Milestone/Plan/Step live in the planner; mountable via IToolProvider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


PlanStateName = Literal["todo", "in_progress", "done", "abandoned"]
STEP_STATES: tuple[PlanStateName, ...] = ("todo", "in_progress", "done", "abandoned")
_ALLOWED_STATE_TRANSITIONS: dict[str, set[str]] = {
    "todo": {"todo", "in_progress", "done", "abandoned"},
    "in_progress": {"in_progress", "done", "abandoned"},
    "done": {"done"},
    "abandoned": {"abandoned"},
}


def is_valid_state_transition(current: str, next_state: str) -> bool:
    """Return whether a plan/step lifecycle transition is legal."""
    if current not in _ALLOWED_STATE_TRANSITIONS:
        return False
    return next_state in _ALLOWED_STATE_TRANSITIONS[current]


def _normalize_state(value: Any, *, default: PlanStateName) -> PlanStateName:
    """Normalize arbitrary values to known lifecycle states."""
    if isinstance(value, str) and value in _ALLOWED_STATE_TRANSITIONS:
        return value
    return default


def _step_id(step: Any) -> str | None:
    """Read step_id from Step-like objects with legacy dict fallback."""
    raw = getattr(step, "step_id", None)
    if raw is None and isinstance(step, dict):
        raw = step.get("step_id")
    if isinstance(raw, str) and raw.strip():
        return raw
    return None


def _step_state(step: Any) -> PlanStateName:
    """Read lifecycle state from Step-like objects with legacy dict fallback."""
    raw = getattr(step, "status", None)
    if raw is None and isinstance(step, dict):
        raw = step.get("status")
    return _normalize_state(raw, default="todo")


def _step_has_explicit_status(step: Any) -> bool:
    """Return True when the step persists status explicitly (object or dict)."""
    if isinstance(step, dict):
        return "status" in step
    return hasattr(step, "status")


# -----------------------------------------------------------------------------
# Input / Output for collaboration
# -----------------------------------------------------------------------------


@dataclass
class Task:
    """Top-level input to a Plan Agent. Not coupled to execution."""

    description: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Milestone:
    """Sub-goal within a task. Used when Plan Agent decomposes a task.

    Each milestone typically has its own plan. Plan Agent can output
    milestones for an orchestrator or for sequential Execution Agents.
    """

    milestone_id: str
    description: str
    success_criteria: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Step: definition + lifecycle state (still no capability_id)
# -----------------------------------------------------------------------------


@dataclass
class Step:
    """Single step: what to do, not how. Which tool to use is decided by executor.

    Verification and remediation happen at milestone level (like dare_agent), but
    runtime lifecycle is explicitly tracked by status.
    """

    step_id: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    status: PlanStateName = "todo"


# -----------------------------------------------------------------------------
# PlannerState: aggregate root
# -----------------------------------------------------------------------------


@dataclass
class PlannerState:
    """Aggregate root: session identity + current plan.

    Holds runtime state for the Planner. When mounted on ReactAgent as IToolProvider,
    the tools (create_plan, validate_plan, verify_milestone, reflect) read/write this state.

    - task_id, session_id: Identity for handoff and audit.
    - milestones: Optional; when Plan Agent decomposes task.
    - current_milestone_id: Which milestone we're planning for.
    - plan_description, steps: Current plan.
    - plan_success, plan_errors: Last validation result.
    - last_verify_errors, last_remediation_summary: Milestone-level (like dare_agent).
    """

    task_id: str = ""
    session_id: str = ""
    # Optional: task decomposition
    milestones: list[Milestone] = field(default_factory=list)
    current_milestone_id: str | None = None
    # Current plan
    plan_description: str = ""
    steps: list[Step] = field(default_factory=list)
    plan_status: PlanStateName = "todo"
    completed_step_ids: set[str] = field(default_factory=set)
    plan_success: bool = True
    plan_errors: list[str] = field(default_factory=list)
    # Plan validated by validate_plan (distinguish from create_plan -> validate_plan flow)
    plan_validated: bool = False
    # Milestone-level verification and remediation (like dare_agent)
    last_verify_errors: list[str] = field(default_factory=list)
    last_remediation_summary: str = ""
    # Critical block: injected into each LLM round. Updated by plan tools when they mutate state.
    critical_block: str = ""

    def sync_completed_step_ids(self) -> None:
        """Rebuild compatibility completed-step set from step statuses."""
        legacy_completed = set(self.completed_step_ids)
        completed: set[str] = set()
        for step in self.steps:
            step_id = _step_id(step)
            if step_id is None:
                continue
            if _step_state(step) == "done":
                completed.add(step_id)
                continue
            # Preserve legacy completion markers for restored sessions where step status
            # was not persisted per-step and only completed_step_ids tracked progress.
            if not _step_has_explicit_status(step) and step_id in legacy_completed:
                completed.add(step_id)
        self.completed_step_ids = completed

    def get_step(self, step_id: str) -> Step | None:
        """Lookup a step by identifier."""
        for step in self.steps:
            if _step_id(step) == step_id:
                return step
        return None

    def transition_plan(self, next_state: PlanStateName) -> None:
        """Transition plan state with legality checks."""
        current = _normalize_state(self.plan_status, default="todo")
        if not isinstance(next_state, str) or next_state not in _ALLOWED_STATE_TRANSITIONS:
            raise ValueError(f"unknown plan state: {next_state}")
        normalized_next = next_state
        if not is_valid_state_transition(current, normalized_next):
            raise ValueError(f"invalid plan transition: {current} -> {normalized_next}")
        self.plan_status = normalized_next

    def transition_step(self, step_id: str, next_state: PlanStateName) -> None:
        """Transition a step state and keep compatibility fields in sync."""
        step = self.get_step(step_id)
        if step is None:
            raise ValueError(f"unknown step_id: {step_id}")
        current = _step_state(step)
        normalized_next = _normalize_state(next_state, default="todo")
        if not is_valid_state_transition(current, normalized_next):
            raise ValueError(f"invalid step transition: {current} -> {normalized_next} ({step_id})")
        if isinstance(step, dict):
            step["status"] = normalized_next
        else:
            setattr(step, "status", normalized_next)
        self.sync_completed_step_ids()

    def copy_for_execution(self) -> PlannerState:
        """Produce clean state for Execution Agent. Strips plan runtime state."""
        steps: list[Step] = []
        for step in self.steps:
            step_id = _step_id(step)
            if not step_id:
                continue
            raw_params = getattr(step, "params", None)
            if raw_params is None and isinstance(step, dict):
                raw_params = step.get("params")
            params = raw_params if isinstance(raw_params, dict) else {}
            raw_description = getattr(step, "description", None)
            if isinstance(step, dict):
                raw_description = step.get("description")
            steps.append(
                Step(
                    step_id=step_id,
                    description=str(raw_description or ""),
                    params=dict(params),
                )
            )
        return PlannerState(
            task_id=self.task_id,
            session_id=self.session_id,
            current_milestone_id=self.current_milestone_id,
            plan_description=self.plan_description,
            steps=steps,
            plan_status="todo",
            plan_success=True,
        )
