"""Tool domain kernel interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence

from dare_framework2.tool.components import ICapabilityProvider
from dare_framework2.tool.types import CapabilityDescriptor

if TYPE_CHECKING:
    from dare_framework2.plan.types import Envelope


class IToolGateway(Protocol):
    """System call boundary and unified invocation entry."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        """List all available capabilities from all providers."""
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        """Invoke a capability within an execution envelope."""
        ...

    def register_provider(self, provider: ICapabilityProvider) -> None:
        """Register a capability provider."""
        ...
