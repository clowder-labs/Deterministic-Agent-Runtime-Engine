"""Protocol adapter provider implementation.

Converts IProtocolAdapter to ICapabilityProvider.
"""

from __future__ import annotations

from typing import Any

from dare_framework.tool.interfaces import ICapabilityProvider, IProtocolAdapter
from dare_framework.tool.types import CapabilityDescriptor, ProviderStatus


class ProtocolAdapterProvider(ICapabilityProvider):
    """Wraps a protocol adapter as a capability provider.
    
    V4 alignment:
    - Translates protocol world into canonical capability model
    - Delegates discovery and invocation to the adapter
    """

    def __init__(self, adapter: IProtocolAdapter) -> None:
        """Initialize with an adapter.
        
        Args:
            adapter: The protocol adapter to wrap.
        """
        self._adapter = adapter
        self._connected = False

    @property
    def protocol_name(self) -> str:
        """Get the wrapped adapter's protocol name."""
        return self._adapter.protocol_name

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        """Connect the adapter to an endpoint.
        
        Args:
            endpoint: The endpoint URL.
            config: Connection configuration.
        """
        await self._adapter.connect(endpoint, config)
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect the adapter."""
        await self._adapter.disconnect()
        self._connected = False

    async def list(self) -> list[CapabilityDescriptor]:
        """List capabilities discovered from the adapter.
        
        Returns:
            List of capabilities from the protocol.
        """
        discovered = await self._adapter.discover()
        return list(discovered)

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        """Invoke a capability through the adapter.
        
        Args:
            capability_id: The capability to invoke.
            params: Parameters to pass.
            
        Returns:
            Result from the adapter invocation.
        """
        return await self._adapter.invoke(capability_id, params)

    async def health_check(self) -> ProviderStatus:
        """Check adapter connection health.
        
        Returns:
            HEALTHY if connected, UNHEALTHY otherwise.
        """
        if self._connected:
            return ProviderStatus.HEALTHY
        return ProviderStatus.UNHEALTHY


__all__ = ["ProtocolAdapterProvider"]
