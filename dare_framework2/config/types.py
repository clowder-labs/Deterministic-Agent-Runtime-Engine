"""Compatibility facade for config models.

Prefer importing from `dare_framework2.config` or `dare_framework2.config.models`.
"""

from dare_framework2.config.models import Config, LLMConfig, ComponentConfig

__all__ = ["Config", "LLMConfig", "ComponentConfig"]
