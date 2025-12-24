from __future__ import annotations

from ..core.interfaces import IValidator
from ..core.models import DonePredicate, Evidence, Milestone, ProposedStep, RunContext, ValidationResult, VerifyResult
from .base_component import BaseComponent


class SimpleValidator(BaseComponent, IValidator):
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


class CompositeValidator(BaseComponent, IValidator):
    def __init__(self, validators: list[IValidator]):
        self._validators = list(validators)

    def _ordered(self) -> list[IValidator]:
        return sorted(self._validators, key=lambda validator: getattr(validator, "order", 100))

    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        errors: list[str] = []
        for validator in self._ordered():
            result = await validator.validate_plan(proposed_steps, ctx)
            if not result.success:
                errors.extend(result.errors)
        return ValidationResult(success=not errors, errors=errors)

    async def validate_milestone(self, milestone: Milestone, result, ctx: RunContext) -> VerifyResult:
        errors: list[str] = []
        evidence: list[Evidence] = []
        success = True
        for validator in self._ordered():
            verify_result = await validator.validate_milestone(milestone, result, ctx)
            if not verify_result.success:
                success = False
                errors.extend(verify_result.errors)
            evidence.extend(verify_result.evidence)
        return VerifyResult(success=success, errors=errors, evidence=evidence)

    async def validate_evidence(self, evidence: list[Evidence], predicate: DonePredicate) -> bool:
        results = [
            await validator.validate_evidence(evidence, predicate)
            for validator in self._ordered()
        ]
        return all(results)
