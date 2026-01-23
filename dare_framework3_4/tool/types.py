"""Tool domain types and execution models for v4.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from dare_framework3_4.security.types import RiskLevel


class ExecutionSignal(Enum):
    """Signals used by the execution control plane."""

    NONE = "none"
    PAUSE_REQUESTED = "pause_requested"
    CANCEL_REQUESTED = "cancel_requested"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"


class PauseRequested(RuntimeError):
    """Raised when a pause is requested."""


class CancelRequested(RuntimeError):
    """Raised when cancellation is requested."""


class HumanApprovalRequired(RuntimeError):
    """Raised when HITL approval is required."""


@dataclass(frozen=True)
class Checkpoint:
    """Checkpoint metadata for pause/resume functionality."""

    id: str
    created_at: float
    event_id: str
    snapshot_ref: str | None = None
    note: str | None = None


class ToolType(Enum):
    """Tool classification used by model adapters and validators."""

    ATOMIC = "atomic"
    WORKUNIT = "workunit"


class CapabilityType(Enum):
    """Canonical capability types."""

    TOOL = "tool"
    AGENT = "agent"
    UI = "ui"


@dataclass
class Evidence:
    """A single evidence record suitable for auditing and verification."""

    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ToolDefinition:
    """Trusted tool metadata exposed to planners/models."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tool_type: ToolType = ToolType.ATOMIC
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    requires_approval: bool = False
    timeout_seconds: int = 30
    produces_assertions: list[dict[str, Any]] = field(default_factory=list)
    is_work_unit: bool = False


ToolSchema = ToolDefinition


@dataclass(frozen=True)
class ToolResult:
    """Canonical tool invocation result, including evidence."""

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ToolErrorRecord:
    """A structured tool error record for remediation/tracing."""

    error_type: str
    tool_name: str
    message: str
    user_hint: str | None = None


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Canonical description of an invokable capability."""

    id: str
    type: CapabilityType
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


DepsT = TypeVar("DepsT")


@dataclass
class RunContext(Generic[DepsT]):
    """A minimal tool execution context."""

    deps: DepsT | None
    run_id: str
    task_id: str | None = None
    milestone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    config: Any | None = None


__all__ = [
    "ExecutionSignal",
    "PauseRequested",
    "CancelRequested",
    "HumanApprovalRequired",
    "Checkpoint",
    "ToolType",
    "CapabilityType",
    "Evidence",
    "ToolDefinition",
    "ToolSchema",
    "ToolResult",
    "ToolErrorRecord",
    "CapabilityDescriptor",
    "RunContext",
]
