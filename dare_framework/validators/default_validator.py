from __future__ import annotations

from dataclasses import dataclass

from dare_framework.components.interfaces import IValidator
from dare_framework.components.toolkit import BasicToolkit
from dare_framework.core.models import (
    DonePredicate,
    Evidence,
    QualityMetrics,
    RunContext,
    StepType,
    ValidationResult,
    ValidatedStep,
    VerifyResult,
)


@dataclass
class DefaultValidator(IValidator):
    toolkit: BasicToolkit

    async def validate_plan(self, proposed_steps, ctx: RunContext) -> ValidationResult:
        validated_steps: list[ValidatedStep] = []
        errors: list[str] = []

        for step in proposed_steps:
            tool = self.toolkit.get_tool(step.tool_name)
            if tool is None:
                errors.append(f"Unknown tool: {step.tool_name}")
                continue

            step_type = StepType.WORKUNIT if tool.tool_type.value == "workunit" else StepType.ATOMIC
            validated_steps.append(
                ValidatedStep(
                    step_id=step.step_id,
                    step_type=step_type,
                    tool_name=tool.name,
                    risk_level=tool.risk_level,
                    tool_input=step.tool_input,
                    description=step.description,
                    envelope=None,
                    done_predicate=None,
                )
            )

        return ValidationResult(is_valid=not errors, validated_steps=validated_steps, errors=errors)

    async def validate_milestone(self, milestone, execute_result, ctx: RunContext) -> VerifyResult:
        passed = execute_result.termination_reason not in {"budget_exceeded", "max_iterations_reached"}
        completeness = 1.0 if passed else 0.0
        return VerifyResult(
            passed=passed,
            completeness=completeness,
            quality_metrics=QualityMetrics(),
            failure_reason=None if passed else "execution_did_not_finish",
        )

    async def validate_evidence(self, evidence: list[Evidence], predicate: DonePredicate) -> bool:
        return predicate.is_satisfied(evidence)
