"""File existence validator for the DARE coding agent example.

This validator implements the IValidator interface correctly:
- validate_plan(): Validates the proposed plan
- verify_milestone(): Verifies milestone completion by checking file existence
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dare_framework.infra.component import ComponentType
from dare_framework.plan.interfaces import IValidator
from dare_framework.plan.types import (
    ProposedPlan,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
    RunResult,
)
from dare_framework.security.types import RiskLevel

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext


class FileExistsValidator(IValidator):
    """Validator that checks for expected files in the workspace.

    This validator:
    - Always passes plan validation (allows all plans)
    - Verifies milestones by checking if expected files exist
    """

    def __init__(
        self,
        workspace: Path,
        expected_files: list[str] | None = None,
        verbose: bool = False,
    ) -> None:
        self._workspace = workspace
        self._expected_files = expected_files or []
        self._verbose = verbose

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.VALIDATOR

    @property
    def name(self) -> str:
        return "file-exists-validator"

    async def validate_plan(
        self, plan: ProposedPlan, ctx: IContext
    ) -> ValidatedPlan:
        """Validate the proposed plan.

        For this example, we accept all plans and convert them to validated plans.
        """
        if self._verbose:
            print(f"[{self.name}] Validating plan with {len(plan.steps)} steps")

        # Convert proposed steps to validated steps
        validated_steps = [
            ValidatedStep(
                step_id=step.step_id,
                capability_id=step.capability_id,
                params=step.params,
                description=step.description,
                risk_level=RiskLevel.READ_ONLY,
            )
            for step in plan.steps
        ]

        if self._verbose:
            print(f"[{self.name}] Plan validated successfully")

        return ValidatedPlan(
            plan_description=plan.plan_description,
            steps=validated_steps,
            success=True,
        )

    def _expected_files_from_plan(self, plan: ValidatedPlan | None) -> list[str]:
        """Collect expected file names from plan steps (e.g. code_creation_evidence)."""
        if plan is None:
            return []
        names: list[str] = []
        for step in plan.steps:
            raw = step.params.get("expected_files")
            if raw is None:
                continue
            if isinstance(raw, list):
                for x in raw:
                    if isinstance(x, str) and x.strip():
                        names.append(x.strip())
            elif isinstance(raw, str) and raw.strip():
                names.append(raw.strip())
        return names

    async def verify_milestone(
        self,
        result: RunResult,
        ctx: IContext,
        *,
        plan: ValidatedPlan | None = None,
    ) -> VerifyResult:
        """Verify milestone completion by checking if expected files exist.

        Expected files come from: (1) plan steps (e.g. code_creation_evidence.params.expected_files),
        or (2) constructor expected_files. So plan-driven verification takes effect when the planner
        emits steps with expected_files (e.g. ['helloworld.py']).
        """
        if self._verbose:
            print(f"[{self.name}] Verifying milestone...")

        # Prefer expected_files from plan steps so dare_agent verification actually runs
        expected = self._expected_files_from_plan(plan) or self._expected_files

        if not expected:
            if self._verbose:
                print(f"[{self.name}] No expected files (plan or config), using execution result")
            return VerifyResult(
                success=result.success,
                errors=result.errors or [],
                metadata={"verification_type": "execution_result"},
            )

        # Check each expected file
        missing_files = []
        found_files = []

        for filename in expected:
            filepath = self._workspace / filename
            if filepath.exists():
                found_files.append(filename)
                if self._verbose:
                    print(f"[{self.name}] ✓ Found: {filename}")
            else:
                missing_files.append(filename)
                if self._verbose:
                    print(f"[{self.name}] ✗ Missing: {filename}")

        if missing_files:
            return VerifyResult(
                success=False,
                errors=[f"Missing files: {', '.join(missing_files)}"],
                metadata={
                    "found_files": found_files,
                    "missing_files": missing_files,
                },
            )

        if self._verbose:
            print(f"[{self.name}] ✓ All expected files found")

        return VerifyResult(
            success=True,
            metadata={
                "found_files": found_files,
                "verification_type": "file_existence",
            },
        )


__all__ = ["FileExistsValidator"]
