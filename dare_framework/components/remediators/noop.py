from __future__ import annotations

from dare_framework.components.base_component import ConfigurableComponent
from dare_framework.core.protocols import IRemediator
from dare_framework.core.plan.results import VerifyResult
from dare_framework.contracts import ComponentType


class NoOpRemediator(ConfigurableComponent, IRemediator):
    """A minimal remediator that turns verification errors into a reflection string."""

    component_type = ComponentType.REMEDIATOR
    name = "noop"

    async def remediate(self, verify_result: VerifyResult, ctx: dict) -> str:
        if verify_result.success:
            return "no-op"
        return "; ".join(verify_result.errors) if verify_result.errors else "remediation required"
