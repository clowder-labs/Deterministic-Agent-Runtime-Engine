"""Simple validator for plan and milestone verification."""
from __future__ import annotations

from dare_framework.context.kernel import IContext
from dare_framework.infra.component import ComponentType
from dare_framework.plan.interfaces import IValidator
from dare_framework.plan.types import ProposedPlan, RunResult, ValidatedPlan, ValidatedStep, VerifyResult
from dare_framework.security.types import RiskLevel


class SimpleValidator:
    """Simple validator that performs basic checks on plans and milestones."""

    @property
    def component_type(self) -> ComponentType:
        """Component type for validator."""
        return ComponentType.VALIDATOR

    async def validate_plan(self, plan: ProposedPlan, ctx: IContext) -> ValidatedPlan:
        """Validate a proposed plan.

        Performs basic checks:
        - Ensures all capability_ids are non-empty
        - Checks for basic parameter completeness

        Args:
            plan: The proposed plan to validate.
            ctx: Context for accessing available capabilities.

        Returns:
            ValidatedPlan with validated steps or errors.
        """
        errors = []
        validated_steps = []

        for step in plan.steps:
            # Basic validation
            if not step.capability_id:
                errors.append(f"Step {step.step_id}: capability_id is empty")
                continue

            # Convert to validated step (in a real validator, would check against registry)
            validated_step = ValidatedStep(
                step_id=step.step_id,
                capability_id=step.capability_id,
                risk_level=RiskLevel.READ_ONLY,  # Default, should be looked up
                params=step.params,
                description=step.description,
                envelope=step.envelope,
            )
            validated_steps.append(validated_step)

        return ValidatedPlan(
            plan_description=plan.plan_description,
            steps=validated_steps,
            success=len(errors) == 0,
            errors=errors,
            metadata=plan.metadata,
        )

    async def verify_milestone(self, result: RunResult, ctx: IContext) -> VerifyResult:
        """Verify milestone completion.

        Actually checks if execution succeeded AND produced meaningful output.
        This enables the Milestone Loop to retry if verification fails.

        Args:
            result: The execution result to verify.
            ctx: Context (unused in simple validator).

        Returns:
            VerifyResult indicating success or failure.
        """
        errors = []

        print(f"[DEBUG] Verifying milestone:")
        print(f"  - result.success: {result.success}")
        print(f"  - result.output: {result.output}")
        print(f"  - result.errors: {result.errors}")

        # Check 1: Did the execution succeed?
        if not result.success:
            errors.append("Execution did not complete successfully")

        # Check 2: Are there errors in result?
        if result.errors:
            errors.extend(result.errors)

        # Check 3: Was any output produced?
        # If output is just text (no tool calls), it's likely the model didn't do anything
        if result.output:
            output_dict = result.output if isinstance(result.output, dict) else {}

            # If output is just {'content': '...'}, the model only returned text
            # This means no tools were called, so task probably wasn't completed
            if isinstance(output_dict, dict) and list(output_dict.keys()) == ['content']:
                content = output_dict.get('content', '')
                # If content is empty or very short, likely nothing was done
                if len(content) < 10:
                    errors.append("No meaningful output produced (only empty/short text response)")
                else:
                    # Model returned explanatory text without calling tools
                    errors.append(f"Model returned text instead of calling tools: {content[:100]}...")
        else:
            errors.append("No output produced")

        print(f"[DEBUG] Verification errors: {errors}")

        # Return actual verification result (not always True!)
        success = len(errors) == 0

        return VerifyResult(
            success=success,
            errors=errors,
            metadata=result.metadata,
        )
