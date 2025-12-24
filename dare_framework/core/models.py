from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Iterable, Literal, Optional, TypeVar
from uuid import uuid4
import time


DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class ToolType(Enum):
    ATOMIC = "atomic"
    WORKUNIT = "workunit"


class StepType(Enum):
    ATOMIC = "atomic"
    WORKUNIT = "workunit"


class RiskLevel(Enum):
    READ_ONLY = "read_only"
    IDEMPOTENT_WRITE = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"
    DESTRUCTIVE = "destructive"


@dataclass
class Task:
    description: str
    task_id: str = field(default_factory=lambda: new_id("task"))
    expectations: list[Expectation] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Expectation:
    expectation_id: str
    description: str
    priority: str
    verification_spec: VerificationSpec


@dataclass
class VerificationSpec:
    type: str
    config: dict[str, Any]


@dataclass
class Milestone:
    milestone_id: str
    description: str
    user_input: str
    order: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunContext(Generic[DepsT]):
    deps: DepsT
    run_id: str


@dataclass
class SessionContext:
    user_input: str
    previous_session_summary: SessionSummary | None
    milestone_summaries: list[MilestoneSummary] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)


@dataclass
class ToolError:
    error_type: str
    tool_name: str
    message: str
    user_hint: str | None = None


@dataclass
class MilestoneContext:
    user_input: str
    milestone_description: str
    reflections: list[str] = field(default_factory=list)
    tool_errors: list[ToolError] = field(default_factory=list)
    evidence_collected: list[Evidence] = field(default_factory=list)
    attempted_plans: list[str] = field(default_factory=list)

    def add_reflection(self, reflection: str) -> "MilestoneContext":
        self.reflections.append(reflection)
        return self

    def add_error(self, error: ToolError) -> "MilestoneContext":
        self.tool_errors.append(error)
        return self


@dataclass
class ProposedPlan:
    plan_description: str
    proposed_steps: list[ProposedStep]


@dataclass
class ProposedStep:
    step_id: str
    tool_name: str
    tool_input: dict[str, Any]
    description: str


@dataclass
class ValidatedPlan:
    plan_description: str
    steps: list[ValidatedStep]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidatedStep:
    step_id: str
    step_type: StepType
    tool_name: str
    risk_level: RiskLevel
    tool_input: dict[str, Any]
    description: str
    envelope: Envelope | None = None
    done_predicate: DonePredicate | None = None


@dataclass
class EnvelopeBudget:
    max_tool_calls: int = 30
    max_tokens: int = 50000
    max_wall_time_seconds: int = 180
    max_stagnant_iterations: int = 3
    current_tool_calls: int = 0
    current_attempts: int = 0
    stagnant_iterations: int = 0
    start_time: float = field(default_factory=time.time)

    def exceeded(self) -> bool:
        if self.current_tool_calls >= self.max_tool_calls:
            return True
        if time.time() - self.start_time >= self.max_wall_time_seconds:
            return True
        if self.stagnant_iterations >= self.max_stagnant_iterations:
            return True
        return False

    def record_attempt(self) -> None:
        self.current_attempts += 1

    def record_tool_call(self) -> None:
        self.current_tool_calls += 1

    def record_stagnation(self) -> None:
        self.stagnant_iterations += 1

    def record_progress(self) -> None:
        self.stagnant_iterations = 0


@dataclass
class Envelope:
    allowed_tools: list[str]
    required_evidence: list[EvidenceCondition]
    budget: EnvelopeBudget
    risk_level: RiskLevel


@dataclass
class Evidence:
    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)


@dataclass
class EvidenceCondition:
    condition_type: str
    params: dict[str, Any]

    def check(self, evidence: Iterable[Evidence]) -> bool:
        if self.condition_type == "always":
            return True
        if self.condition_type == "evidence_kind":
            kind = self.params.get("kind")
            return any(item.kind == kind for item in evidence)
        if self.condition_type == "evidence_id":
            evidence_id = self.params.get("id")
            return any(item.evidence_id == evidence_id for item in evidence)
        return False


@dataclass
class InvariantCondition:
    condition_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def check(self) -> bool:
        if self.condition_type == "always":
            return True
        return True


@dataclass
class DonePredicate:
    evidence_conditions: list[EvidenceCondition]
    invariant_conditions: list[InvariantCondition]

    def is_satisfied(self, evidence: Iterable[Evidence]) -> bool:
        for condition in self.evidence_conditions:
            if not condition.check(evidence):
                return False
        for invariant in self.invariant_conditions:
            if not invariant.check():
                return False
        return True


@dataclass
class ExecuteResult:
    evidence: list[Evidence]
    successful_tool_calls: list[dict[str, Any]]
    execution_trace: list[dict[str, Any]]
    encountered_plan_tool: bool = False
    plan_tool_name: str | None = None
    termination_reason: Literal[
        "llm_declares_done",
        "plan_tool_encountered",
        "budget_exceeded",
        "max_iterations_reached",
    ] | None = None
    llm_conclusion: str | None = None


@dataclass
class QualityMetrics:
    tests_passing: int = 0
    tests_failing: int = 0
    lint_errors: int = 0
    files_modified: int = 0


@dataclass
class VerifyResult:
    passed: bool
    completeness: float
    quality_metrics: QualityMetrics
    failure_reason: str | None = None
    missing_evidence: list[str] = field(default_factory=list)
    violated_invariants: list[str] = field(default_factory=list)


@dataclass
class MilestoneResult:
    milestone_id: str
    deliverables: list[str]
    evidence: list[Evidence]
    quality_metrics: QualityMetrics
    completeness: float
    last_verify_result: VerifyResult | None
    attempts: int
    tool_calls: int
    duration_seconds: float
    termination_reason: Literal[
        "verify_pass",
        "budget_exceeded",
        "stagnant",
        "plan_generation_failed",
    ]
    errors: list[ToolError] = field(default_factory=list)


@dataclass
class MilestoneSummary:
    milestone_id: str
    milestone_description: str
    deliverables: list[str]
    what_worked: str
    what_failed: str
    key_insight: str
    completeness: float
    termination_reason: str
    attempts: int
    duration_seconds: float


@dataclass
class SessionSummary:
    session_id: str
    user_input: str
    what_was_accomplished: str
    key_deliverables: list[str]
    important_decisions: list[str]
    lessons_learned: list[str]
    pending_tasks: list[str]
    milestone_count: int
    total_attempts: int
    duration_seconds: float


@dataclass
class Budget:
    max_attempts: int = 10
    max_time_seconds: int = 600
    max_tool_calls: int = 100
    current_attempts: int = 0
    current_tool_calls: int = 0
    start_time: float = field(default_factory=time.time)

    def exceeded(self) -> bool:
        if self.current_attempts >= self.max_attempts:
            return True
        if time.time() - self.start_time >= self.max_time_seconds:
            return True
        if self.current_tool_calls >= self.max_tool_calls:
            return True
        return False

    def record_attempt(self) -> None:
        self.current_attempts += 1

    def record_tool_call(self) -> None:
        self.current_tool_calls += 1


@dataclass
class ToolResult:
    success: bool
    output: Any
    evidence_ref: Evidence | None = None
    error: Any | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    tool_type: ToolType | None = None
    risk_level: RiskLevel | None = None
    is_plan_tool: bool = False


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCall] | None = None


@dataclass
class GenerateOptions:
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass
class ModelResponse:
    content: str
    tool_calls: list[ToolCall]


@dataclass
class ValidationResult:
    is_valid: bool
    validated_steps: list[ValidatedStep]
    errors: list[str] = field(default_factory=list)


@dataclass
class SessionResult:
    session_summary: SessionSummary


@dataclass
class RunResult(Generic[OutputT]):
    success: bool
    output: OutputT | None = None
    session_summary: SessionSummary | None = None
    error: str | None = None


@dataclass
class MemoryItem:
    key: str
    value: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssembledContext:
    milestone_description: str
    reflections: list[str]
    previous_summaries: list[MilestoneSummary]
    memory_items: list[MemoryItem]
    additional_context: dict[str, Any] = field(default_factory=dict)
