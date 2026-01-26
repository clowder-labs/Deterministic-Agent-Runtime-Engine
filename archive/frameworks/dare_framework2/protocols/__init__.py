"""Protocol adapters domain (Layer 1)."""

from dare_framework2.protocols.base import IProtocolAdapter
from dare_framework2.protocols.mcp.interfaces import IMCPClient

__all__ = [
    "IProtocolAdapter",
    "IMCPClient",
]
