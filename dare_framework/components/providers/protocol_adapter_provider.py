from __future__ import annotations

from typing import Any

from dare_framework.core.tool.capabilities import CapabilityDescriptor, ICapabilityProvider
from dare_framework.protocols.base import IProtocolAdapter


class ProtocolAdapterProvider(ICapabilityProvider):
    """Expose a protocol adapter as a capability provider for the Kernel gateway."""

    def __init__(self, adapter: IProtocolAdapter) -> None:
        self._adapter = adapter

    async def list(self) -> list[CapabilityDescriptor]:
        return list(await self._adapter.discover())

    async def invoke(self, capability_id: str, params: dict[str, Any]) -> object:
        return await self._adapter.invoke(capability_id, params)
