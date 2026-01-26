"""Config domain: configuration management.

This domain handles loading, resolving, and providing
configuration to the framework.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.config.component import IConfigProvider

# Common types
from dare_framework3_2.config.types import Config

# Default implementations
from dare_framework3_2.config.impl.default_config_provider import DefaultConfigProvider

__all__ = [
    # Protocol
    "IConfigProvider",
    # Types
    "Config",
    # Implementations
    "DefaultConfigProvider",
]
