"""tool domain stable interfaces (Kernel boundaries).

Alignment notes:
- All side-effects MUST flow through `IToolGateway.invoke(...)`.
- HITL control plane lives behind `IExecutionControl`.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework.config.types import Config
from dare_framework.plan.types import Envelope
from dare_framework.tool.types import (
    CapabilityDescriptor,
    ExecutionSignal,
    ProviderStatus,
    ToolDefinition,
    ToolResult,
)


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

    # NOTE: Forward references avoid importing tool.interfaces into the kernel layer.

    def load_tools(self, *, config: Config | None = None) -> list["ITool"]:
        """Load tool implementations from configuration."""
        ...

    def register_tool(
        self,
        tool: "ITool",
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
        tool: "ITool",
        *,
        capability_id: str,
        enabled: bool | None = None,
    ) -> CapabilityDescriptor:
        """Update a registered tool capability."""
        ...

    def set_capability_enabled(self, capability_id: str, enabled: bool) -> None:
        """Enable or disable a capability in the registry."""
        ...

    def register_provider(self, provider: "IToolProvider") -> None:
        """Register a tool provider."""
        ...

    def unregister_provider(self, provider: "IToolProvider") -> bool:
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


class IExecutionControl(Protocol):
    """Control plane for pause/resume/checkpoints (HITL)."""

    def poll(self) -> ExecutionSignal: ...

    def poll_or_raise(self) -> None: ...

    async def pause(self, reason: str) -> str: ...

    async def resume(self, checkpoint_id: str) -> None: ...

    async def checkpoint(self, label: str, payload: dict[str, Any]) -> str: ...

    async def wait_for_human(self, checkpoint_id: str, reason: str) -> None: ...


__all__ = ["IExecutionControl", "IToolGateway", "IToolManager"]
