"""tool domain stable interfaces (Kernel boundaries).

Alignment notes:
- All side-effects MUST flow through `IToolGateway.invoke(...)`.
- HITL control plane lives behind `IExecutionControl` in tool.interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Sequence

from dare_framework.config.types import Config
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolDefinition,
    ToolResult,
    ToolType,
)

if TYPE_CHECKING:
    from dare_framework.plan.types import Envelope
    from dare_framework.context import Context


class IToolProvider(ABC):
    """[Component] Tool provider interface (core)."""

    @abstractmethod
    def list_tools(self) -> list[ITool]:
        """Get available tool instances for registration."""
        ...


class ITool(IComponent, ABC):
    """A callable tool implementation (core contract)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.TOOL]:
        """Component category used for config scoping."""
        return ComponentType.TOOL

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema inferred from execute signature and parameter docs."""
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any] | None:
        """JSON schema inferred from execute return annotation and docs."""
        return infer_output_schema_from_execute(type(self).execute)

    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        """Tool classification (atomic or work unit)."""
        ...

    @property
    @abstractmethod
    def risk_level(self) -> RiskLevelName:
        """Security risk classification (trusted registry source)."""
        ...

    @property
    @abstractmethod
    def requires_approval(self) -> bool:
        """Whether human approval is required (trusted registry source)."""
        ...

    @property
    @abstractmethod
    def timeout_seconds(self) -> int:
        """Execution timeout in seconds."""
        ...

    @property
    @abstractmethod
    def is_work_unit(self) -> bool:
        """Whether this tool is a work unit (envelope-bounded loop)."""
        ...

    @property
    @abstractmethod
    def capability_kind(self) -> CapabilityKind:
        """Capability kind for trusted registry metadata."""
        ...

    @abstractmethod
    async def execute(self, *, run_context: RunContext[Any], **params: Any) -> ToolResult[Any]:
        """Execute the tool and return a ToolResult."""
        ...


class IToolGateway(ABC):
    """System-call boundary and trusted capability registry facade."""

    @abstractmethod
    def list_capabilities(self) -> list[CapabilityDescriptor]: ...

    @abstractmethod
    async def invoke(
            self,
            capability_id: str,
            *,
            envelope: Envelope,
            context: Context | None = None,
            **params: Any,
    ) -> ToolResult:
        """Invoke a registered tool capability."""
        ...


class IToolManager(ABC):
    """Trusted tool registry and management interface."""

    @abstractmethod
    def load_tools(self, *, config: Config | None = None) -> list[ITool]:
        """Load tool implementations from configuration."""
        ...

    @abstractmethod
    def register_tool(
            self,
            tool: ITool,
            *,
            namespace: str | None = None,
            version: str | None = None,
    ) -> CapabilityDescriptor:
        """Register a tool and return its capability descriptor."""
        ...

    @abstractmethod
    def get_tool(self, capability_id: str) -> ITool:
        ...

    @abstractmethod
    def unregister_tool(self, capability_id: str) -> bool:
        """Unregister a tool capability by id."""
        ...

    @abstractmethod
    def change_capability_status(self, capability_id: str, enabled: bool) -> None:
        """Enable or disable a capability in the registry."""
        ...

    @abstractmethod
    def register_provider(self, provider: IToolProvider) -> None:
        """Register a tool provider."""
        ...

    @abstractmethod
    def unregister_provider(self, provider: IToolProvider) -> bool:
        """Unregister a tool provider."""
        ...

    @abstractmethod
    async def refresh(self) -> list[CapabilityDescriptor]:
        """Refresh provider tools into the registry."""
        ...

    @abstractmethod
    def list_capabilities(
            self,
            *,
            include_disabled: bool = False,
    ) -> list[CapabilityDescriptor]:
        """List registered capabilities."""
        ...

    @abstractmethod
    def get_capability(
            self,
            capability_id: str,
            *,
            include_disabled: bool = False,
    ) -> CapabilityDescriptor | None:
        """Fetch a capability descriptor by id."""
        ...


__all__ = ["ITool", "IToolGateway", "IToolManager", "IToolProvider"]
