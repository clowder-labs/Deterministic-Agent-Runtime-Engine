"""plan_v2 types - self-contained, no dependency on dare_framework.plan.

Design principles (from discussion):
- Plan Agent and Execution Agent are separate; copy_for_execution() passes clean state.
- Step does NOT specify capability_id; executor decides which tools to use.
- Milestone/Plan/Step live in the planner; mountable via IToolProvider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
# Step: definition only (no capability_id, no runtime state)
# -----------------------------------------------------------------------------


@dataclass
class Step:
    """Single step: what to do, not how. Which tool to use is decided by executor.

    Step is pure definition. Verification and remediation happen at milestone level
    (like dare_agent), not per-step.
    """

    step_id: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)


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

    def copy_for_execution(self) -> PlannerState:
        """Produce clean state for Execution Agent. Strips plan runtime state."""
        steps = [
            Step(step_id=s.step_id, description=s.description, params=dict(s.params))
            for s in self.steps
        ]
        return PlannerState(
            task_id=self.task_id,
            session_id=self.session_id,
            current_milestone_id=self.current_milestone_id,
            plan_description=self.plan_description,
            steps=steps,
            plan_success=True,
        )
