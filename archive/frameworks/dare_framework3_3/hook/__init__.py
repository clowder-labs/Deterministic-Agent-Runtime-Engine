"""Hook domain: extension points and hook phases."""

from dare_framework3_3.hook.kernel import IExtensionPoint
from dare_framework3_3.hook.component import IHook
from dare_framework3_3.hook.types import HookPhase
from dare_framework3_3.hook.internal.default_extension_point import DefaultExtensionPoint
from dare_framework3_3.hook.internal.noop_hook import NoOpHook

__all__ = [
    "IExtensionPoint",
    "IHook",
    "HookPhase",
    "DefaultExtensionPoint",
    "NoOpHook",
]
