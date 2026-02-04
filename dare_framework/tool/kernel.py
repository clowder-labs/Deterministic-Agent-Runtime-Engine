"""tool domain stable interfaces (Kernel boundaries).

Alignment notes:
- All side-effects MUST flow through `IToolGateway.invoke(...)`.
- HITL control plane lives behind `IExecutionControl` in tool.interfaces.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, Sequence, runtime_checkable

from dare_framework.config.types import Config
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.plan.types import Envelope
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    ProviderStatus,
    RiskLevelName,
    RunContext,
    ToolDefinition,
    ToolResult,
    ToolType,
)


@runtime_checkable
class IToolProvider(Protocol):
    """[Component] Tool provider interface (core)."""

    def list_tools(self) -> list["ITool"]:
        """Get available tool instances for registration."""
        ...


@runtime_checkable
class ITool(IComponent, Protocol):
    """A callable tool implementation (core contract)."""

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.TOOL]:
        """Component category used for config scoping."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for input validation."""
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        """JSON schema for output validation."""
        ...

    @property
    def tool_type(self) -> ToolType:
        """Tool classification (atomic or work unit)."""
        ...

    @property
    def risk_level(self) -> RiskLevelName:
        """Security risk classification (trusted registry source)."""
        ...

    @property
    def requires_approval(self) -> bool:
        """Whether human approval is required (trusted registry source)."""
        ...

    @property
    def timeout_seconds(self) -> int:
        """Execution timeout in seconds."""
        ...

    @property
    def is_work_unit(self) -> bool:
        """Whether this tool is a work unit (envelope-bounded loop)."""
        ...

    @property
    def capability_kind(self) -> CapabilityKind:
        """Capability kind for trusted registry metadata."""
        ...

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        """Execute the tool and return a ToolResult."""
        ...


class IToolGateway(Protocol):
    """System-call boundary and trusted capability registry facade."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: Envelope,
    ) -> Any: ...

    def register_provider(self, provider: object) -> None: ...


@runtime_checkable
class IToolManager(IToolGateway, Protocol):
    """Trusted tool registry and management interface."""

    def load_tools(self, *, config: Config | None = None) -> list[ITool]:
        """Load tool implementations from configuration."""
        ...

    def register_tool(
        self,
        tool: ITool,
        *,
        namespace: str | None = None,
        version: str | None = None,
    ) -> CapabilityDescriptor:
        """Register a tool and return its capability descriptor."""
        ...

    def unregister_tool(self, capability_id: str) -> bool:
        """Unregister a tool capability by id."""
        ...

    def update_tool(
        self,
        tool: ITool,
        *,
        capability_id: str,
        enabled: bool | None = None,
    ) -> CapabilityDescriptor:
        """Update a registered tool capability."""
        ...

    def set_capability_enabled(self, capability_id: str, enabled: bool) -> None:
        """Enable or disable a capability in the registry."""
        ...

    def register_provider(self, provider: IToolProvider) -> None:
        """Register a tool provider."""
        ...

    def unregister_provider(self, provider: IToolProvider) -> bool:
        """Unregister a tool provider."""
        ...

    async def refresh(self) -> list[CapabilityDescriptor]:
        """Refresh provider tools into the registry."""
        ...

    async def list_capabilities(
        self,
        *,
        include_disabled: bool = False,
    ) -> list[CapabilityDescriptor]:
        """List registered capabilities."""
        ...

    def list_tool_defs(self) -> list[ToolDefinition]:
        """List tool definitions derived from the registry."""
        ...

    def get_capability(
        self,
        capability_id: str,
        *,
        include_disabled: bool = False,
    ) -> CapabilityDescriptor | None:
        """Fetch a capability descriptor by id."""
        ...

    async def health_check(self) -> dict[str, ProviderStatus]:
        """Check provider health status."""
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: Envelope,
    ) -> ToolResult:
        """Invoke a registered tool capability."""
        ...


__all__ = ["ITool", "IToolGateway", "IToolManager", "IToolProvider"]
