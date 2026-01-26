"""Kernel tool gateway protocols (v2)."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from dare_framework.plan.envelope import Envelope
from dare_framework.tool.components import ICapabilityProvider
from dare_framework.tool.types import CapabilityDescriptor


class IToolGateway(Protocol):
    """System call boundary and unified invocation entry (v2.0)."""

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]: ...

    async def invoke(self, capability_id: str, params: dict[str, Any], *, envelope: Envelope) -> Any: ...

    def register_provider(self, provider: ICapabilityProvider) -> None: ...
