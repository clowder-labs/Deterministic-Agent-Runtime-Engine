"""Deterministic planner for testing."""
from __future__ import annotations

from dare_framework.context.kernel import IContext
from dare_framework.infra.component import ComponentType
from dare_framework.plan.interfaces import IPlanner
from dare_framework.plan.types import ProposedPlan, ProposedStep


class DeterministicPlanner:
    """Deterministic planner that returns a predefined plan.

    Used for testing and validation without requiring real model calls.
    """

    def __init__(self, plan: ProposedPlan):
        """Initialize with a predefined plan.

        Args:
            plan: The plan to return when plan() is called.
        """
        self._plan = plan

    @property
    def component_type(self) -> ComponentType:
        """Component type for planner."""
        return ComponentType.PLANNER

    async def plan(self, ctx: IContext) -> ProposedPlan:
        """Return the predefined plan.

        Args:
            ctx: Context (unused in deterministic mode).

        Returns:
            The predefined plan.
        """
        return self._plan
