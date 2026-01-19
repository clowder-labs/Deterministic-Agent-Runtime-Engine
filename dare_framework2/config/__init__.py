"""Config domain: framework configuration management.

This domain handles configuration models and layered merging utilities.
"""

from dare_framework2.config.manager import ConfigManager, merge_config_layers, build_config_from_layers
from dare_framework2.config.models import Config, LLMConfig, ComponentConfig

__all__ = [
    "ConfigManager",
    "merge_config_layers",
    "build_config_from_layers",
    "Config",
    "LLMConfig",
    "ComponentConfig",
]
