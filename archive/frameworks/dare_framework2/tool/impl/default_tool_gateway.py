"""Default tool gateway implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

from dare_framework2.tool.kernel import IToolGateway
from dare_framework2.tool.components import ICapabilityProvider
from dare_framework2.tool.types import CapabilityDescriptor

if TYPE_CHECKING:
    from dare_framework2.plan.types import Envelope


class DefaultToolGateway(IToolGateway):
    """Aggregates multiple capability providers into a single invocation surface.
    
    The default gateway:
    - Collects capabilities from all registered providers
    - Enforces envelope allow-lists
    - Routes invocations to the appropriate provider
    """

    def __init__(self) -> None:
        self._providers: list[ICapabilityProvider] = []
        self._capability_to_provider: dict[str, ICapabilityProvider] = {}

    def register_provider(self, provider: ICapabilityProvider) -> None:
        """Register a capability provider."""
        self._providers.append(provider)
        # Mapping is rebuilt during list_capabilities()

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        """List all capabilities from all providers."""
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

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        """Invoke a capability within an envelope."""
        # Check envelope allow-list
        if envelope.allowed_capability_ids and capability_id not in envelope.allowed_capability_ids:
            raise PermissionError(f"Capability '{capability_id}' not allowed by envelope")

        # Find the provider
        provider = self._capability_to_provider.get(capability_id)
        if provider is None:
            # Refresh mapping lazily for dynamic providers
            await self.list_capabilities()
            provider = self._capability_to_provider.get(capability_id)
        
        if provider is None:
            raise KeyError(f"Unknown capability id: {capability_id}")

        return await provider.invoke(capability_id, params)
