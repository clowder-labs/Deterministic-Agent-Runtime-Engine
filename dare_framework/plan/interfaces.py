"""plan domain pluggable interfaces (strategies)."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.context.kernel import IContext
from dare_framework.plan.types import ProposedPlan, RunResult, ValidatedPlan, VerifyResult


class IPlanner(Protocol):
    async def plan(self, ctx: IContext) -> ProposedPlan: ...


class IValidator(Protocol):
    async def validate_plan(self, plan: ProposedPlan, ctx: IContext) -> ValidatedPlan: ...

    async def verify_milestone(self, result: RunResult, ctx: IContext) -> VerifyResult: ...


class IRemediator(Protocol):
    async def remediate(self, verify_result: VerifyResult, ctx: IContext) -> str: ...

class IPlannerManager(Protocol):
    """Loads a planner strategy implementation (single-select)."""

    def load_planner(self, *, config: Any | None = None) -> object | None: ...


class IValidatorManager(Protocol):
    """Loads validator strategy implementations (multi-load)."""

    def load_validators(self, *, config: Any | None = None) -> list[object]: ...


class IRemediatorManager(Protocol):
    """Loads a remediation strategy implementation (single-select)."""

    def load_remediator(self, *, config: Any | None = None) -> object | None: ...


__all__ = [
    "IPlanner",
    "IPlannerManager",
    "IRemediator",
    "IRemediatorManager",
    "IValidator",
    "IValidatorManager",
]
