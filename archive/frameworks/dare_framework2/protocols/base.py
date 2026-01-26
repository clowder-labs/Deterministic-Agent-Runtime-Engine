"""Protocol adapter interfaces (Layer 1)."""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework2.tool.types import CapabilityDescriptor


@runtime_checkable
class IProtocolAdapter(Protocol):
    """Protocol adapter contract (Layer 1)."""

    @property
    def protocol_name(self) -> str:
        """The name of the protocol (e.g., 'mcp', 'a2a')."""
        ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        """Connect to the protocol endpoint."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the protocol endpoint."""
        ...

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        """Discover remote capabilities."""
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any:
        """Invoke a remote capability."""
        ...
