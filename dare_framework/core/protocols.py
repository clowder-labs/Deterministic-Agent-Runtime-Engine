from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework.core.context import AssembledContext, Prompt
from dare_framework.core.plan.planning import ProposedPlan, ValidatedPlan
from dare_framework.core.plan.results import ExecuteResult, VerifyResult


@runtime_checkable
class IPlanner(Protocol):
    """Planning strategy interface (Layer 2)."""

    async def plan(self, ctx: AssembledContext) -> ProposedPlan: ...


@runtime_checkable
class IValidator(Protocol):
    """Validation strategy interface (Layer 2)."""

    async def validate_plan(self, plan: ProposedPlan, ctx: dict) -> ValidatedPlan: ...

    async def verify_milestone(self, result: ExecuteResult, ctx: dict) -> VerifyResult: ...


@runtime_checkable
class IRemediator(Protocol):
    """Remediation strategy interface (Layer 2)."""

    async def remediate(self, verify_result: VerifyResult, ctx: dict) -> str: ...


@runtime_checkable
class IContextStrategy(Protocol):
    """Prompt/context assembly strategy interface (Layer 2)."""

    async def build_prompt(self, assembled: AssembledContext) -> Prompt: ...
