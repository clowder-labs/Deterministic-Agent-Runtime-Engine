"""plan domain pluggable interfaces (strategies)."""

from __future__ import annotations

from typing import Literal, Protocol

from dare_framework.config.types import Config
from dare_framework.context.kernel import IContext
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.plan.types import (
    ProposedPlan,
    RunResult,
    ValidatedPlan,
    VerifyResult,
)


class IPlanner(IComponent, Protocol):
    """Plan generator that emits untrusted ProposedPlan output."""

    @property
    def component_type(self) -> Literal[ComponentType.PLANNER]:
        ...

    async def plan(self, ctx: IContext) -> ProposedPlan: ...


class IValidator(IComponent, Protocol):
    """Plan and milestone validator that derives trusted plan state.

    Implementations SHOULD derive security-critical fields (e.g., risk metadata)
    from trusted registries rather than planner/model output.
    """

    @property
    def component_type(self) -> Literal[ComponentType.VALIDATOR]:
        ...

    async def validate_plan(self, plan: ProposedPlan, ctx: IContext) -> ValidatedPlan: ...

    async def verify_milestone(
        self,
        result: RunResult,
        ctx: IContext,
        *,
        plan: ValidatedPlan | None = None,
    ) -> VerifyResult: ...


class IRemediator(IComponent, Protocol):
    """Produces reflection text to guide the next planning attempt."""

    @property
    def component_type(self) -> Literal[ComponentType.REMEDIATOR]:
        ...

    async def remediate(self, verify_result: VerifyResult, ctx: IContext) -> str: ...


class IPlannerManager(Protocol):
    """Loads a planner strategy implementation (single-select)."""

    def load_planner(self, *, config: Config | None = None) -> IPlanner | None: ...


class IValidatorManager(Protocol):
    """Loads validator strategy implementations (multi-load)."""

    def load_validators(self, *, config: Config | None = None) -> list[IValidator]: ...


class IRemediatorManager(Protocol):
    """Loads a remediation strategy implementation (single-select)."""

    def load_remediator(self, *, config: Config | None = None) -> IRemediator | None: ...


__all__ = [
    "IPlanner",
    "IPlannerManager",
    "IRemediator",
    "IRemediatorManager",
    "IValidator",
    "IValidatorManager",
]
