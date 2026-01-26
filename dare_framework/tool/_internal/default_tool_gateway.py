"""Default ToolGateway implementation (canonical baseline)."""

from __future__ import annotations

from typing import Any, Sequence

from dare_framework.plan.types import Envelope
from dare_framework.tool.interfaces import ICapabilityProvider
from dare_framework.tool.kernel import IToolGateway
from dare_framework.tool.types import CapabilityDescriptor


class DefaultToolGateway(IToolGateway):
    """Aggregate capability providers into a single invocation surface."""

    def __init__(self) -> None:
        self._providers: list[ICapabilityProvider] = []
        self._capability_to_provider: dict[str, ICapabilityProvider] = {}

    def register_provider(self, provider: object) -> None:
        self._providers.append(provider)  # Expect ICapabilityProvider; rely on duck-typing.

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        capabilities: list[CapabilityDescriptor] = []
        mapping: dict[str, ICapabilityProvider] = {}
        for provider in self._providers:
            for capability in await provider.list():
                if capability.id in mapping:
                    raise ValueError(f"Duplicate capability id: {capability.id}")
                mapping[capability.id] = provider
                capabilities.append(capability)
        self._capability_to_provider = mapping
        return capabilities

    async def invoke(self, capability_id: str, params: dict[str, Any], *, envelope: Envelope) -> Any:
        if envelope.allowed_capability_ids and capability_id not in envelope.allowed_capability_ids:
            raise PermissionError(f"Capability '{capability_id}' not allowed by envelope")

        provider = self._capability_to_provider.get(capability_id)
        if provider is None:
            await self.list_capabilities()
            provider = self._capability_to_provider.get(capability_id)
        if provider is None:
            raise KeyError(f"Unknown capability id: {capability_id}")

        return await provider.invoke(capability_id, params)


__all__ = ["DefaultToolGateway"]
