"""tool domain types (v3.4; v4-style capability model)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypeAlias, TypedDict


@dataclass
class Evidence:
    """A single evidence record suitable for auditing and verification."""

    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ToolResult:
    """Canonical tool invocation result, including evidence.

    Used for compatibility with 3.2 output format.
    """

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


class ExecutionSignal(Enum):
    """Signals used by the runtime to pause/cancel or request HITL."""

    NONE = "none"
    PAUSE_REQUESTED = "pause_requested"
    CANCEL_REQUESTED = "cancel_requested"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"


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


ToolDefinition: TypeAlias = dict[str, Any]


__all__ = [
    "CapabilityDescriptor",
    "CapabilityKind",
    "CapabilityMetadata",
    "CapabilityType",
    "Evidence",
    "ExecutionSignal",
    "RiskLevelName",
    "ToolDefinition",
    "ToolResult",
]
