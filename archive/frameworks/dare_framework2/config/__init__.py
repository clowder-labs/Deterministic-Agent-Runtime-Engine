"""Config domain: framework configuration management.

This domain handles configuration loading, merging, and provision
for the framework and its components.
"""

from dare_framework2.config.interfaces import IConfigProvider
from dare_framework2.config.types import Config, LLMConfig, ComponentConfig

__all__ = [
    # Interfaces
    "IConfigProvider",
    # Types
    "Config",
    "LLMConfig",
    "ComponentConfig",
]
