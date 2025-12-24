from __future__ import annotations

from ..core.interfaces import IValidator
from ..core.models import DonePredicate, Evidence, Milestone, ProposedStep, RunContext, ValidationResult, VerifyResult


class SimpleValidator(IValidator):
    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        if not proposed_steps:
            return ValidationResult(success=False, errors=["Plan has no steps"])
        return ValidationResult(success=True, errors=[])

    async def validate_milestone(self, milestone: Milestone, result, ctx: RunContext) -> VerifyResult:
        if result.success:
            return VerifyResult(success=True, errors=[], evidence=[])
        return VerifyResult(success=False, errors=result.errors, evidence=[])

    async def validate_evidence(self, evidence: list[Evidence], predicate: DonePredicate) -> bool:
        if not predicate.required_keys and not predicate.evidence_conditions:
            return True
        if predicate.required_keys:
            available_keys = set()
            for item in evidence:
                if isinstance(item.payload, dict):
                    available_keys.update(item.payload.keys())
            if not set(predicate.required_keys).issubset(available_keys):
                return False
        if predicate.evidence_conditions:
            checks = [condition.check(evidence) for condition in predicate.evidence_conditions]
            return all(checks) if predicate.require_all else any(checks)
        return True
