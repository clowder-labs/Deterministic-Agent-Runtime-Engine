"""Step executor for step-driven execution mode.

Executes validated plan steps sequentially, collecting evidence
for milestone verification.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dare_framework.plan.types import (
    Envelope,
    Evidence,
    StepResult,
    ValidatedStep,
)

if TYPE_CHECKING:
    from dare_framework.context.kernel import IContext
    from dare_framework.tool.kernel import IToolGateway


class DefaultEvidenceCollector:
    """Default implementation of IEvidenceCollector.

    Creates structured Evidence objects from execution outputs.
    """

    def collect(
        self,
        source: str,
        data: dict[str, Any],
        evidence_type: str,
    ) -> Evidence:
        """Create an Evidence object from execution output.

        Args:
            source: Capability ID or validation source.
            data: Evidence payload data.
            evidence_type: Type of evidence (tool_result, file_hash, etc.).

        Returns:
            Evidence object for storage and verification.
        """
        return Evidence(
            evidence_id=f"ev_{uuid4().hex[:8]}",
            evidence_type=evidence_type,
            source=source,
            data=data,
            timestamp=datetime.now(),
        )


class DefaultStepExecutor:
    """Default implementation of IStepExecutor.

    Executes validated steps by invoking tools via IToolGateway
    and collecting evidence from results.

    Example:
        executor = DefaultStepExecutor(tool_gateway)
        result = await executor.execute_step(step, ctx, [])
    """

    def __init__(
        self,
        tool_gateway: IToolGateway,
        evidence_collector: DefaultEvidenceCollector | None = None,
    ) -> None:
        """Initialize step executor.

        Args:
            tool_gateway: Gateway for tool invocations.
            evidence_collector: Optional collector, creates default if None.
        """
        self._gateway = tool_gateway
        self._collector = evidence_collector or DefaultEvidenceCollector()

    async def execute_step(
        self,
        step: ValidatedStep,
        ctx: IContext,
        previous_results: list[StepResult],
    ) -> StepResult:
        """Execute a single validated step.

        Args:
            step: The step to execute.
            ctx: Current context.
            previous_results: Results from previously executed steps.

        Returns:
            StepResult with execution outcome and evidence.
        """
        try:
            # Build context from previous results if needed
            step_context = self._build_step_context(step, previous_results)

            # Invoke tool via gateway
            result = await self._gateway.invoke(
                step.capability_id,
                envelope=step.envelope or Envelope(),
                **{**step.params, **step_context},
            )

            # Collect evidence from result
            evidence = self._collector.collect(
                source=step.capability_id,
                data={"result": result, "params": step.params},
                evidence_type="tool_result",
            )

            return StepResult(
                step_id=step.step_id,
                success=True,
                output=result,
                evidence=[evidence],
            )

        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                errors=[str(e)],
            )

    def _build_step_context(
        self,
        step: ValidatedStep,
        previous_results: list[StepResult],
    ) -> dict[str, Any]:
        """Build additional context from previous step results.

        Args:
            step: Current step.
            previous_results: Results from prior steps.

        Returns:
            Context dict to merge with step params.
        """
        if not previous_results:
            return {}

        # Provide last successful result as context
        last_success = next(
            (r for r in reversed(previous_results) if r.success),
            None,
        )

        if last_success:
            return {"_previous_output": last_success.output}

        return {}


__all__ = ["DefaultEvidenceCollector", "DefaultStepExecutor"]
