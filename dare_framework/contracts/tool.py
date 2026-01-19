"""Tool capability contracts and canonical tool I/O types (v2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from dare_framework.contracts.evidence import Evidence
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.run_context import RunContext


class ToolType(Enum):
    """Tool classification used by model adapters and validators."""

    ATOMIC = "atomic"
    WORKUNIT = "workunit"


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


@runtime_checkable
class ITool(Protocol):
    """Executable tool contract used by NativeToolProvider and examples.

    Notes:
    - Tools are capability implementations. In v2, side effects must still be routed
      through the Kernel `IToolGateway` boundary, but tool implementations are kept
      as plain Python objects for ease of extension.
    """

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def input_schema(self) -> dict[str, Any]: ...

    @property
    def output_schema(self) -> dict[str, Any]: ...

    @property
    def tool_type(self) -> ToolType: ...

    @property
    def risk_level(self) -> RiskLevel: ...

    @property
    def requires_approval(self) -> bool: ...

    @property
    def timeout_seconds(self) -> int: ...

    @property
    def produces_assertions(self) -> list[dict[str, Any]]: ...

    @property
    def is_work_unit(self) -> bool: ...

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult: ...

