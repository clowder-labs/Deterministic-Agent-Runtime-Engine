"""plan domain pluggable interfaces (strategies)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from dare_framework.config.types import Config
from dare_framework.context.kernel import IContext
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.plan.types import (
    DecompositionResult,
    Evidence,
    Milestone,
    ProposedPlan,
    RunResult,
    StepResult,
    Task,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
)


class IPlanner(IComponent, ABC):
    """Plan generator that emits untrusted ProposedPlan output.

    Implementations can also decompose tasks into milestones via decompose().
    """

    @property
    def component_type(self) -> Literal[ComponentType.PLANNER]:
        return ComponentType.PLANNER

    @abstractmethod
    async def plan(self, ctx: IContext) -> ProposedPlan:
        """Generate a plan for the current milestone."""
        ...

    async def decompose(self, task: Task, ctx: IContext) -> DecompositionResult:
        """Decompose a task into milestones.

        Default implementation returns a single milestone from task description.
        Override this method to enable LLM-driven task decomposition.

        Args:
            task: The task to decompose.
            ctx: Current context.

        Returns:
            DecompositionResult with milestones and reasoning.
        """
        from uuid import uuid4

        return DecompositionResult(
            milestones=[
                Milestone(
                    milestone_id=f"{task.task_id or uuid4().hex[:8]}_m1",
                    description=task.description,
                    user_input=(
                        task.input_message.text
                        if task.input_message is not None and task.input_message.text
                        else task.description
                    ),
                )
            ],
            reasoning="Default: single milestone from task description",
        )


class IValidator(IComponent, ABC):
    """Plan and milestone validator that derives trusted plan state.

    Implementations SHOULD derive security-critical fields (e.g., risk metadata)
    from trusted registries rather than planner/model output.
    """

    @property
    def component_type(self) -> Literal[ComponentType.VALIDATOR]:
        return ComponentType.VALIDATOR

    @abstractmethod
    async def validate_plan(self, plan: ProposedPlan, ctx: IContext) -> ValidatedPlan: ...

    @abstractmethod
    async def verify_milestone(
            self,
            result: RunResult,
            ctx: IContext,
            *,
            plan: ValidatedPlan | None = None,
    ) -> VerifyResult: ...


class IRemediator(IComponent, ABC):
    """Produces reflection text to guide the next planning attempt."""

    @property
    def component_type(self) -> Literal[ComponentType.REMEDIATOR]:
        return ComponentType.REMEDIATOR

    @abstractmethod
    async def remediate(self, verify_result: VerifyResult, ctx: IContext) -> str: ...


class IPlanAttemptSandbox(ABC):
    """State isolation interface for plan attempts.

    Provides snapshot/rollback capability to ensure failed plan attempts
    do not pollute milestone context.
    """

    @abstractmethod
    def create_snapshot(self, ctx: IContext) -> str:
        """Create a snapshot of the current STM state.

        Args:
            ctx: Context containing STM to snapshot.

        Returns:
            Unique snapshot_id for later rollback or commit.
        """
        ...

    @abstractmethod
    def rollback(self, ctx: IContext, snapshot_id: str) -> None:
        """Rollback STM to a previous snapshot state.

        Args:
            ctx: Context containing STM to restore.
            snapshot_id: ID from create_snapshot().
        """
        ...

    @abstractmethod
    def commit(self, snapshot_id: str) -> None:
        """Discard a snapshot, keeping current state.

        Args:
            snapshot_id: ID of snapshot to discard.
        """
        ...


class IStepExecutor(ABC):
    """Executes individual plan steps in step-driven mode.

    Used by Execute Loop when execution_mode="step_driven" to execute
    ValidatedPlan.steps sequentially.
    """

    @abstractmethod
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
        ...


class IEvidenceCollector(ABC):
    """Collects structured evidence during execution.

    Evidence is used for milestone verification and audit trails.
    """

    @abstractmethod
    def collect(
            self,
            source: str,
            data: dict,
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
        ...


class IPlannerManager(ABC):
    """Loads a planner strategy implementation (single-select)."""

    @abstractmethod
    def load_planner(self, *, config: Config | None = None) -> IPlanner | None: ...


class IValidatorManager(ABC):
    """Loads validator strategy implementations (multi-load)."""

    @abstractmethod
    def load_validators(self, *, config: Config | None = None) -> list[IValidator]: ...


class IRemediatorManager(ABC):
    """Loads a remediation strategy implementation (single-select)."""

    @abstractmethod
    def load_remediator(self, *, config: Config | None = None) -> IRemediator | None: ...


__all__ = [
    "IEvidenceCollector",
    "IPlanner",
    "IPlanAttemptSandbox",
    "IPlannerManager",
    "IRemediator",
    "IRemediatorManager",
    "IStepExecutor",
    "IValidator",
    "IValidatorManager",
]
