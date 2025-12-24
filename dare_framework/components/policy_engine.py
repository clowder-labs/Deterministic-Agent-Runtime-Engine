from __future__ import annotations

from dataclasses import dataclass, field

from dare_framework.components.interfaces import IPolicyEngine, ITool, PolicyDecision
from dare_framework.core.errors import PolicyDeniedError
from dare_framework.core.models import Milestone, RunContext, RiskLevel, ValidatedPlan


@dataclass
class AllowAllPolicy(IPolicyEngine):
    approval_required_for: set[RiskLevel] = field(default_factory=set)

    def check_tool_access(self, tool: ITool, ctx: RunContext) -> PolicyDecision:
        return PolicyDecision.ALLOW

    def needs_approval(self, milestone: Milestone, validated_plan: ValidatedPlan) -> bool:
        if not self.approval_required_for:
            return False
        for step in validated_plan.steps:
            if step.risk_level in self.approval_required_for:
                return True
        return False

    def enforce(self, action: str, resource: str, ctx: RunContext) -> None:
        return None


@dataclass
class DenyAllPolicy(IPolicyEngine):
    def check_tool_access(self, tool: ITool, ctx: RunContext) -> PolicyDecision:
        return PolicyDecision.DENY

    def needs_approval(self, milestone: Milestone, validated_plan: ValidatedPlan) -> bool:
        return True

    def enforce(self, action: str, resource: str, ctx: RunContext) -> None:
        raise PolicyDeniedError("Policy denied action")
