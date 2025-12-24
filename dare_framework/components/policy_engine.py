from __future__ import annotations

from ..core.interfaces import IPolicyEngine
from ..core.models import Milestone, PolicyDecision, RunContext, ValidatedPlan


class AllowAllPolicyEngine(IPolicyEngine):
    def check_tool_access(self, tool, ctx: RunContext) -> PolicyDecision:
        return PolicyDecision.ALLOW

    def needs_approval(self, milestone: Milestone, validated_plan: ValidatedPlan) -> bool:
        return False

    def enforce(self, action: str, resource: str, ctx: RunContext) -> None:
        return None
