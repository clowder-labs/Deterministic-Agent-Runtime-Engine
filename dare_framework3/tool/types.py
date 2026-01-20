"""Tool domain data types."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar


# =============================================================================
# Enums
# =============================================================================

class RiskLevel(Enum):
    """Risk level classification for capabilities that may have side effects.
    
    Values:
        READ_ONLY: No side effects, safe to execute
        IDEMPOTENT_WRITE: Safe to retry without additional effects
        COMPENSATABLE: Has side effects but can be rolled back
        NON_IDEMPOTENT_EFFECT: Has permanent side effects, requires approval
    """
    READ_ONLY = "read_only"
    IDEMPOTENT_WRITE = "idempotent_write"
    COMPENSATABLE = "compensatable"
    NON_IDEMPOTENT_EFFECT = "non_idempotent_effect"


class ToolType(Enum):
    """Tool classification used by model adapters and validators.
    
    Values:
        ATOMIC: Single invocation tool
        WORKUNIT: May require multiple invocations to complete
    """
    ATOMIC = "atomic"
    WORKUNIT = "workunit"


class CapabilityType(Enum):
    """Canonical capability types.
    
    Values:
        TOOL: A tool capability (local or remote)
        AGENT: An A2A peer agent capability
        UI: An A2UI rendering/input capability
    """
    TOOL = "tool"
    AGENT = "agent"
    UI = "ui"


class PolicyDecision(Enum):
    """Policy decision returned by ISecurityBoundary.check_policy.
    
    Values:
        ALLOW: Action is permitted
        DENY: Action is denied
        APPROVE_REQUIRED: Action requires human approval
    """
    ALLOW = "allow"
    DENY = "deny"
    APPROVE_REQUIRED = "approve_required"


# =============================================================================
# Evidence
# =============================================================================

@dataclass
class Evidence:
    """A single evidence record suitable for auditing and verification.
    
    Attributes:
        evidence_id: Unique identifier
        kind: Type of evidence (e.g., "command", "file", "test")
        payload: Evidence data
        created_at: Unix timestamp of creation
    """
    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Tool Types
# =============================================================================

@dataclass(frozen=True)
class ToolDefinition:
    """Trusted tool metadata exposed to planners/models.
    
    Attributes:
        name: Unique tool name
        description: Human-readable description
        input_schema: JSON Schema for input validation
        output_schema: JSON Schema for output
        tool_type: Atomic or work unit
        risk_level: Security risk classification
        requires_approval: Whether HITL approval is needed
        timeout_seconds: Execution timeout
        produces_assertions: Assertions this tool can produce
        is_work_unit: Whether this is a work unit tool
    """
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


@dataclass(frozen=True)
class ToolResult:
    """Canonical tool invocation result, including evidence.
    
    Attributes:
        success: Whether the tool execution succeeded
        output: Tool output data
        error: Error message if failed
        evidence: Supporting evidence
    """
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ToolErrorRecord:
    """A structured tool error record for remediation/tracing.
    
    Attributes:
        error_type: Classification of the error
        tool_name: Name of the tool that errored
        message: Error message
        user_hint: Optional hint for the user
    """
    error_type: str
    tool_name: str
    message: str
    user_hint: str | None = None


# =============================================================================
# Capability Descriptor
# =============================================================================

@dataclass(frozen=True)
class CapabilityDescriptor:
    """Canonical description of an invokable capability.
    
    Attributes:
        id: Unique capability identifier
        type: Capability type (tool, agent, ui)
        name: Human-readable name
        description: Description of what the capability does
        input_schema: JSON Schema for input
        output_schema: JSON Schema for output
        metadata: Additional capability metadata
    """
    id: str
    type: CapabilityType
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


# =============================================================================
# Run Context
# =============================================================================

DepsT = TypeVar("DepsT")


@dataclass
class RunContext(Generic[DepsT]):
    """A minimal tool execution context.
    
    Provides tools with information about the current execution state.
    Intentionally small with serializable fields.
    
    Attributes:
        deps: User-provided dependencies
        run_id: Current run identifier
        task_id: Current task identifier
        milestone_id: Current milestone identifier
        metadata: Additional context data
        config: Optional configuration object
    """
    deps: DepsT | None
    run_id: str
    task_id: str | None = None
    milestone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    config: Any | None = None


# =============================================================================
# Security Types
# =============================================================================

@dataclass(frozen=True)
class TrustedInput:
    """Trusted input derived from untrusted params + registries.
    
    Attributes:
        params: Validated parameters
        risk_level: Trusted risk level from registry
        metadata: Additional security metadata
    """
    params: dict[str, Any]
    risk_level: RiskLevel
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SandboxSpec:
    """Minimal sandbox specification placeholder.
    
    The MVP may stub sandbox behavior, but keeps the contract surface.
    
    Attributes:
        mode: Sandbox mode (e.g., "stub", "docker", "seccomp")
        details: Mode-specific configuration
    """
    mode: str = "stub"
    details: dict[str, Any] = field(default_factory=dict)
