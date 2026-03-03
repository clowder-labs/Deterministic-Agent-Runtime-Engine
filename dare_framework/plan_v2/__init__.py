"""plan_v2 - Standalone planner for Plan Agent / Execution Agent separation.

Does not depend on dare_framework.plan. Mount on ReactAgent via IToolProvider.
"""

from dare_framework.plan_v2.planner import Planner
from dare_framework.plan_v2.registry import SubAgentRegistry
from dare_framework.plan_v2.types import (
    Milestone,
    PlanStateName,
    PlannerState,
    STEP_STATES,
    Step,
    Task,
    is_valid_state_transition,
)
from dare_framework.plan_v2.prompts import PLAN_AGENT_SYSTEM_PROMPT, SUB_AGENT_TASK_PROMPT
from dare_framework.plan_v2.tools import (
    CreatePlanTool,
    DecomposeTaskTool,
    DelegateToSubAgentTool,
    FinishPlanTool,
    ReflectTool,
    ReviseCurrentPlanTool,
    ValidatePlanTool,
    VerifyMilestoneTool,
)

__all__ = [
    "CreatePlanTool",
    "DecomposeTaskTool",
    "DelegateToSubAgentTool",
    "FinishPlanTool",
    "Milestone",
    "PLAN_AGENT_SYSTEM_PROMPT",
    "PlanStateName",
    "Planner",
    "SUB_AGENT_TASK_PROMPT",
    "STEP_STATES",
    "PlannerState",
    "ReflectTool",
    "ReviseCurrentPlanTool",
    "Step",
    "SubAgentRegistry",
    "Task",
    "ValidatePlanTool",
    "VerifyMilestoneTool",
    "is_valid_state_transition",
]
