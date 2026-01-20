"""Hook domain: extension points and hook phases."""

from dare_framework3.hook.component import IExtensionPoint, IHook
from dare_framework3.hook.types import HookPhase
from dare_framework3.hook.impl.default_extension_point import DefaultExtensionPoint
from dare_framework3.hook.impl.noop_hook import NoOpHook

__all__ = [
    "IExtensionPoint",
    "IHook",
    "HookPhase",
    "DefaultExtensionPoint",
    "NoOpHook",
]
