from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from dare_framework.core.tool.capabilities import CapabilityDescriptor


@runtime_checkable
class IProtocolAdapter(Protocol):
    """Protocol adapter contract (v2.0 Layer 1)."""

    @property
    def protocol_name(self) -> str: ...

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None: ...

    async def disconnect(self) -> None: ...

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        """Discover remote capabilities and translate them into canonical descriptors."""

    async def invoke(self, capability_id: str, params: dict[str, Any], *, timeout: float | None = None) -> Any: ...
