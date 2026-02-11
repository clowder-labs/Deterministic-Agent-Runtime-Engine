"""plan_v2 - Standalone planner for Plan Agent / Execution Agent separation.

Does not depend on dare_framework.plan. Mount on ReactAgent via IToolProvider.
"""

from dare_framework.plan_v2.planner import Planner
from dare_framework.plan_v2.registry import SubAgentRegistry
from dare_framework.plan_v2.types import (
    Milestone,
    PlannerState,
    Step,
    Task,
)
from dare_framework.plan_v2.prompts import PLAN_AGENT_SYSTEM_PROMPT, SUB_AGENT_TASK_PROMPT
from dare_framework.plan_v2.tools import (
    CreatePlanTool,
    DecomposeTaskTool,
    DelegateToSubAgentTool,
    ReflectTool,
    ValidatePlanTool,
    VerifyMilestoneTool,
)

__all__ = [
    "CreatePlanTool",
    "DecomposeTaskTool",
    "DelegateToSubAgentTool",
    "Milestone",
    "PLAN_AGENT_SYSTEM_PROMPT",
    "Planner",
    "SUB_AGENT_TASK_PROMPT",
    "PlannerState",
    "ReflectTool",
    "Step",
    "SubAgentRegistry",
    "Task",
    "ValidatePlanTool",
    "VerifyMilestoneTool",
]
