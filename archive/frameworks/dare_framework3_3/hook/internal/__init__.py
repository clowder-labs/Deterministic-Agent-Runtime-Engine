"""Hook domain implementations."""

from dare_framework3_3.hook.internal.default_extension_point import DefaultExtensionPoint
from dare_framework3_3.hook.internal.noop_hook import NoOpHook

__all__ = ["DefaultExtensionPoint", "NoOpHook"]
