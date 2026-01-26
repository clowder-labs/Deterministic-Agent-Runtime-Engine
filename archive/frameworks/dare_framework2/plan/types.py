"""Plan domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterable

from dare_framework2.utils.ids import generate_id

if TYPE_CHECKING:
    from dare_framework2.tool.types import ToolResult, Evidence, RiskLevel
    from dare_framework2.execution.types import Budget


# =============================================================================
# Task and Milestone
# =============================================================================

@dataclass
class Milestone:
    """A single closed-loop objective within a task.
    
    Represents a discrete goal that can be planned, executed, and verified.
    
    Attributes:
        milestone_id: Unique identifier
        description: Human-readable description
        user_input: The original user input for this milestone
        order: Execution order (lower = earlier)
        metadata: Additional milestone data
    """
    milestone_id: str
    description: str
    user_input: str
    order: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A high-level execution request.
    
    Represents the top-level goal provided by the user.
    May be decomposed into multiple milestones.
    
    Attributes:
        description: The task description
        task_id: Unique identifier (auto-generated if not provided)
        context: Additional context data
        constraints: Execution constraints
        milestones: Optional pre-defined milestones
        created_at: Task creation timestamp
    """
    description: str
    task_id: str = field(default_factory=lambda: generate_id("task"))
    context: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    milestones: list[Milestone] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_milestones(self) -> list[Milestone]:
        """Derive milestones from the task when none are provided."""
        if self.milestones is not None:
            return self.milestones
        return [
            Milestone(
                milestone_id=generate_id("milestone"),
                description=self.description,
                user_input=self.description,
                order=0,
            )
        ]


# =============================================================================
# Plan Proposals (Untrusted - from Planner)
# =============================================================================

@dataclass(frozen=True)
class ProposedStep:
    """Untrusted step proposal produced by the planner.
    
    Security note: All fields should be treated as untrusted input.
    The validator will derive trusted fields from registries.
    
    Attributes:
        step_id: Unique step identifier
        capability_id: The capability to invoke
        params: Parameters for the capability
        description: Human-readable description
        envelope: Optional execution boundary
    """
    step_id: str
    capability_id: str
    params: dict[str, Any]
    description: str = ""
    envelope: "Envelope | None" = None


@dataclass(frozen=True)
class ProposedPlan:
    """Untrusted plan proposal produced by the planner.
    
    Attributes:
        plan_description: Human-readable plan description
        steps: List of proposed steps
        attempt: The attempt number (for retry tracking)
        metadata: Additional plan metadata
    """
    plan_description: str
    steps: list[ProposedStep]
    attempt: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Validated Plan (Trusted - from Validator)
# =============================================================================

@dataclass(frozen=True)
class ValidatedStep:
    """Trusted step derived from registries and policy/trust checks.
    
    Security note: risk_level is derived from the trusted capability registry,
    not from the planner's proposal.
    
    Attributes:
        step_id: Unique step identifier
        capability_id: The capability to invoke
        risk_level: Trusted risk level from registry
        params: Parameters for the capability
        description: Human-readable description
        envelope: Execution boundary
    """
    step_id: str
    capability_id: str
    risk_level: "RiskLevel"
    params: dict[str, Any]
    description: str = ""
    envelope: "Envelope | None" = None


@dataclass(frozen=True)
class ValidatedPlan:
    """A validated plan safe for execution.
    
    Attributes:
        plan_description: Human-readable plan description
        steps: List of validated steps
        metadata: Additional plan metadata
        validated_at: Validation timestamp
        success: Whether validation succeeded
        errors: Validation error messages
    """
    plan_description: str
    steps: list[ValidatedStep]
    metadata: dict[str, Any] = field(default_factory=dict)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Envelope and Done Predicate
# =============================================================================

@dataclass(frozen=True)
class EvidenceCondition:
    """A minimal, deterministic evidence predicate used by DonePredicate.
    
    Attributes:
        condition_type: The type of condition ("always", "evidence_kind", etc.)
        params: Condition-specific parameters
    """
    condition_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def check(self, evidence: Iterable["Evidence"]) -> bool:
        """Check if the condition is satisfied by the evidence."""
        if self.condition_type == "always":
            return True
        if self.condition_type == "evidence_kind":
            kind = self.params.get("kind")
            return any(item.kind == kind for item in evidence)
        return False


@dataclass(frozen=True)
class DonePredicate:
    """Defines what 'done' means for a Tool Loop attempt.
    
    Attributes:
        required_keys: Keys that must be present in evidence
        evidence_conditions: Conditions to check against evidence
        require_all: Whether all conditions must be met (vs any)
        description: Human-readable description
    """
    required_keys: list[str] = field(default_factory=list)
    evidence_conditions: list[EvidenceCondition] = field(default_factory=list)
    require_all: bool = True
    description: str | None = None


def _default_budget() -> "Budget":
    """Lazy import to avoid circular dependency."""
    from dare_framework2.execution.types import Budget
    return Budget()


def _default_risk_level() -> "RiskLevel":
    """Lazy import to avoid circular dependency."""
    from dare_framework2.tool.types import RiskLevel
    return RiskLevel.READ_ONLY


@dataclass(frozen=True)
class Envelope:
    """Execution boundary for the Tool Loop.
    
    Defines constraints on what capabilities can be invoked and
    how resources are allocated within a tool loop.
    
    Attributes:
        allowed_capability_ids: Allow-list of capabilities (empty = no restriction)
        budget: Resource budget for this envelope
        done_predicate: Condition for considering the loop complete
        risk_level: The risk level for this execution
    """
    allowed_capability_ids: list[str] = field(default_factory=list)
    budget: "Budget" = field(default_factory=_default_budget)
    done_predicate: DonePredicate | None = None
    risk_level: "RiskLevel" = field(default_factory=_default_risk_level)


@dataclass(frozen=True)
class ToolLoopRequest:
    """Tool Loop invocation payload.
    
    Security note:
    - capability_id/params MUST be treated as untrusted from model output
    - Security-critical fields MUST be derived from trusted registries
    
    Attributes:
        capability_id: The capability to invoke
        params: Parameters for the capability
        envelope: Execution boundary
    """
    capability_id: str
    params: dict[str, Any] = field(default_factory=dict)
    envelope: Envelope = field(default_factory=Envelope)


# =============================================================================
# Execution Results
# =============================================================================

@dataclass(frozen=True)
class ToolLoopResult:
    """Tool Loop output used by the orchestrator.
    
    Attributes:
        success: Whether the tool loop succeeded
        result: The final tool result
        attempts: Number of attempts made
    """
    success: bool
    result: "ToolResult"
    attempts: int


@dataclass(frozen=True)
class ExecuteResult:
    """Execute Loop output, including tool results and re-plan signals.
    
    Attributes:
        success: Whether execution succeeded
        outputs: List of tool results
        errors: Error messages
        encountered_plan_tool: Whether a plan tool was encountered
        plan_tool_name: Name of the plan tool (if encountered)
    """
    success: bool
    outputs: list["ToolResult"] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    encountered_plan_tool: bool = False
    plan_tool_name: str | None = None


@dataclass(frozen=True)
class VerifyResult:
    """Verification output for a milestone.
    
    Attributes:
        success: Whether verification passed
        errors: Error messages
        evidence: Supporting evidence
    """
    success: bool
    errors: list[str] = field(default_factory=list)
    evidence: list["Evidence"] = field(default_factory=list)


# =============================================================================
# Summaries
# =============================================================================

@dataclass(frozen=True)
class MilestoneSummary:
    """Summary of a milestone execution.
    
    Attributes:
        milestone_id: The milestone identifier
        description: Milestone description
        success: Whether the milestone succeeded
        attempt_count: Number of attempts made
        evidence_count: Amount of evidence collected
    """
    milestone_id: str
    description: str
    success: bool
    attempt_count: int
    evidence_count: int


@dataclass(frozen=True)
class MilestoneResult:
    """Complete result of a milestone execution.
    
    Attributes:
        success: Whether the milestone succeeded
        outputs: Tool outputs
        errors: Error messages
        verify_result: Verification result
        summary: Milestone summary
    """
    success: bool
    outputs: list["ToolResult"] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    verify_result: VerifyResult | None = None
    summary: MilestoneSummary | None = None


@dataclass(frozen=True)
class SessionSummary:
    """Summary of a session execution.
    
    Attributes:
        session_id: Session identifier
        milestone_count: Number of milestones
        success: Whether the session succeeded
        completed_at: Completion timestamp
    """
    session_id: str
    milestone_count: int
    success: bool
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RunResult:
    """Top-level execution result returned to developers.
    
    Attributes:
        success: Whether the run succeeded
        output: Final output (from last milestone)
        milestone_results: Results for each milestone
        errors: Error messages
        session_summary: Session summary
    """
    success: bool
    output: Any | None = None
    milestone_results: list[MilestoneResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    session_summary: SessionSummary | None = None
