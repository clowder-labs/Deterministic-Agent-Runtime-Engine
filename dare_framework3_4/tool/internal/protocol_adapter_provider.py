"""Protocol adapter provider implementation."""

from __future__ import annotations

from typing import Any

from dare_framework3_4.tool.interfaces import ICapabilityProvider, IProtocolAdapter
from dare_framework3_4.tool.types import CapabilityDescriptor, ProviderStatus


class ProtocolAdapterProvider(ICapabilityProvider):
    """Expose a protocol adapter as a capability provider."""

    def __init__(self, adapter: IProtocolAdapter) -> None:
        self._adapter = adapter

    async def list(self) -> list[CapabilityDescriptor]:
        return list(await self._adapter.discover())

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        return await self._adapter.invoke(capability_id, params)

    async def health_check(self) -> ProviderStatus:
        return ProviderStatus.HEALTHY
