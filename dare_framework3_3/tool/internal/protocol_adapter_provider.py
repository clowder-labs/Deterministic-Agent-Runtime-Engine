"""Protocol adapter provider implementation."""

from __future__ import annotations

from typing import Any

from dare_framework3_3.tool.component import ICapabilityProvider, IProtocolAdapter
from dare_framework3_3.tool.types import CapabilityDescriptor


class ProtocolAdapterProvider(ICapabilityProvider):
    """Expose a protocol adapter as a capability provider.
    
    Bridges protocol adapters (MCP, A2A, etc.) to the Kernel gateway.
    
    Args:
        adapter: The protocol adapter to wrap
    """

    def __init__(self, adapter: IProtocolAdapter) -> None:
        self._adapter = adapter

    async def list(self) -> list[CapabilityDescriptor]:
        """List capabilities from the adapter."""
        return list(await self._adapter.discover())

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
    ) -> object:
        """Invoke a capability via the adapter."""
        return await self._adapter.invoke(capability_id, params)
