"""Kernel hook domain (v2)."""

from .models import HookPhase
from .protocols import IExtensionPoint
from .default_extension_point import DefaultExtensionPoint

__all__ = ["HookPhase", "IExtensionPoint", "DefaultExtensionPoint"]
