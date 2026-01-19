from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework.core.plan.envelope import Envelope
from dare_framework.core.tool.capabilities import CapabilityDescriptor, ICapabilityProvider


class IToolGateway(Protocol):
    """System call boundary and unified invocation entry (v2.0)."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any], *, envelope: Envelope) -> Any: ...

    def register_provider(self, provider: ICapabilityProvider) -> None: ...
