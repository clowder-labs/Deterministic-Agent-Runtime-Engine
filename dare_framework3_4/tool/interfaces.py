"""tool domain pluggable interfaces (implementations).

This module intentionally focuses on interface declarations only.
Concrete implementations (native tools, protocol adapters, gateways) live under
`_internal/` when introduced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, Sequence, TypeVar, runtime_checkable

from dare_framework3_4.tool.types import CapabilityDescriptor, ToolResult


@runtime_checkable
class IToolProvider(Protocol):
    """[Component] Tool provider interface.

    Usage: Injected into BaseContext.tools.
    Provides tool listing capability for context assembly.

    Note: This is a minimal interface for BaseContext integration.
    Tool execution boundaries and control-plane contracts are declared in
    `dare_framework3_4.tool.kernel` (v4-style alignment).
    """

    def list_tools(self) -> list[dict[str, Any]]:
        """Get available tool definitions in LLM-compatible format.

        Returns:
            List of tool definitions with name, description, parameters, etc.
        """
        ...

TDeps = TypeVar("TDeps")


@dataclass(frozen=True)
class RunContext(Generic[TDeps]):
    """Invocation context passed into tools."""

    deps: TDeps | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ITool(Protocol):
    """A callable tool implementation."""

    @property
    def name(self) -> str: ...

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult: ...


@runtime_checkable
class ICapabilityProvider(Protocol):
    """A provider that exposes capabilities to a ToolGateway registry."""

    async def list(self) -> list[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object: ...


@runtime_checkable
class IProtocolAdapter(Protocol):
    """Protocol adapter (e.g., MCP/A2A) translated into canonical capabilities."""

    @property
    def protocol_name(self) -> str: ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None: ...

    async def disconnect(self) -> None: ...

    async def discover(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any: ...


__all__ = [
    "ICapabilityProvider",
    "IProtocolAdapter",
    "ITool",
    "IToolProvider",
    "RunContext",
    "ToolResult",
]
