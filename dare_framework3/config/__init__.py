"""Config domain: framework configuration management.

This domain handles configuration loading, merging, and provision
for the framework and its components.

Factory Functions:
    create_default_config_provider: Create default IConfigProvider
"""

from __future__ import annotations

from dare_framework3.config.interfaces import IConfigProvider
from dare_framework3.config.types import Config, LLMConfig, ComponentConfig

__all__ = [
    # Interfaces
    "IConfigProvider",
    # Types
    "Config",
    "LLMConfig",
    "ComponentConfig",
    # Factory functions
    "create_default_config_provider",
]


# =============================================================================
# Factory Functions
# =============================================================================

def create_default_config_provider() -> IConfigProvider:
    """Create the default IConfigProvider implementation.
    
    Returns:
        A DefaultConfigProvider instance
    """
    from dare_framework3.config.impl.default_config_provider import DefaultConfigProvider
    return DefaultConfigProvider()
