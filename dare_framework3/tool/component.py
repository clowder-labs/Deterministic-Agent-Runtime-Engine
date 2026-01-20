"""Tool domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence, runtime_checkable

from dare_framework3.security.types import RiskLevel
from dare_framework3.tool.types import (
    ToolResult,
    ToolType,
    CapabilityDescriptor,
    CapabilityType,
    RunContext,
    ToolDefinition,
    ExecutionSignal,
)

if TYPE_CHECKING:
    from dare_framework3.plan.types import Envelope


@runtime_checkable
class ITool(Protocol):
    """Executable tool contract."""

    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        ...

    @property
    def tool_type(self) -> ToolType:
        ...

    @property
    def risk_level(self) -> RiskLevel:
        ...

    @property
    def requires_approval(self) -> bool:
        ...

    @property
    def timeout_seconds(self) -> int:
        ...

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        ...

    @property
    def is_work_unit(self) -> bool:
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        ...


@runtime_checkable
class ISkill(Protocol):
    """A pluggable skill capability."""

    @property
    def name(self) -> str:
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        ...


class ICapabilityProvider(Protocol):
    """Provides capabilities to the tool gateway."""

    async def list(self) -> list[CapabilityDescriptor]:
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
    ) -> object:
        ...


class IToolGateway(Protocol):
    """System call boundary and unified invocation entry."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        ...

    def register_provider(self, provider: ICapabilityProvider) -> None:
        ...


@runtime_checkable
class IProtocolAdapter(Protocol):
    """Protocol adapter contract (Layer 1)."""

    @property
    def protocol_name(self) -> str:
        ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        ...

    async def disconnect(self) -> None:
        ...

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any:
        ...


@runtime_checkable
class IMCPClient(Protocol):
    """Minimal MCP client interface for remote tools."""

    @property
    def name(self) -> str:
        ...

    @property
    def transport(self) -> str:
        ...

    async def connect(self) -> None:
        ...

    async def disconnect(self) -> None:
        ...

    async def list_tools(self) -> list[ToolDefinition]:
        ...

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        ...


class IExecutionControl(Protocol):
    """Pause/resume/checkpoint control plane."""

    def poll(self) -> ExecutionSignal:
        ...

    def poll_or_raise(self) -> None:
        ...

    async def pause(self, reason: str) -> str:
        ...

    async def resume(self, checkpoint_id: str) -> None:
        ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str:
        ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None:
        ...


__all__ = [
    "ITool",
    "ISkill",
    "ICapabilityProvider",
    "IToolGateway",
    "IProtocolAdapter",
    "IMCPClient",
    "IExecutionControl",
    "ToolType",
    "CapabilityType",
]
