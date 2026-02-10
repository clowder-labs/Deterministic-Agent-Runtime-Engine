"""Tool domain types (capability model)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Literal, TypeAlias, TypedDict, TypeVar


class ExecutionSignal(Enum):
    """Signals used by the runtime to pause/cancel or request HITL."""

    NONE = "none"
    PAUSE_REQUESTED = "pause_requested"
    CANCEL_REQUESTED = "cancel_requested"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"


class ToolType(Enum):
    """Tool classification for execution semantics."""

    ATOMIC = "atomic"  # Single-shot execution
    WORK_UNIT = "work_unit"  # Envelope-bounded loop


class ProviderStatus(Enum):
    """Health status for capability providers."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InvocationContext:
    """Context for tracing and managing a single tool invocation."""

    invocation_id: str
    capability_id: str
    parent_id: str | None = None
    started_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityType(Enum):
    """Canonical capability types."""

    TOOL = "tool"
    AGENT = "agent"
    UI = "ui"


class CapabilityKind(Enum):
    """Optional capability sub-kinds used by trusted registries."""

    TOOL = "tool"
    SKILL = "skill"
    PLAN_TOOL = "plan_tool"
    AGENT = "agent"
    UI = "ui"


RiskLevelName: TypeAlias = Literal[
    "read_only",
    "idempotent_write",
    "compensatable",
    "non_idempotent_effect",
]


class CapabilityMetadata(TypedDict, total=False):
    """Trusted capability metadata derived from registries (not model output)."""

    risk_level: RiskLevelName
    requires_approval: bool
    timeout_seconds: int
    is_work_unit: bool
    capability_kind: CapabilityKind


@dataclass
class Evidence:
    """A single evidence record suitable for auditing and verification."""

    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)


OutputT = TypeVar("OutputT")


@dataclass(frozen=True)
class ToolResult(Generic[OutputT]):
    """Canonical tool invocation result, including evidence."""

    success: bool
    output: OutputT | dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ToolErrorRecord:
    """A structured tool error record for remediation/tracing."""

    error_type: str
    tool_name: str
    message: str
    user_hint: str | None = None


ToolDefinition: TypeAlias = dict[str, Any]
ToolSchema = ToolDefinition


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Canonical description of an invokable capability."""

    id: str
    type: CapabilityType
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    metadata: CapabilityMetadata | None = None


DepsT = TypeVar("DepsT")


@dataclass
class RunContext(Generic[DepsT]):
    """Invocation context passed into tools."""

    deps: DepsT | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""
    task_id: str | None = None
    milestone_id: str | None = None
    config: Any | None = None


__all__ = [
    "CapabilityDescriptor",
    "CapabilityKind",
    "CapabilityMetadata",
    "CapabilityType",
    "Evidence",
    "ExecutionSignal",
    "InvocationContext",
    "ProviderStatus",
    "RiskLevelName",
    "ToolDefinition",
    "ToolSchema",
    "ToolErrorRecord",
    "ToolResult",
    "ToolType",
    "RunContext",
]
