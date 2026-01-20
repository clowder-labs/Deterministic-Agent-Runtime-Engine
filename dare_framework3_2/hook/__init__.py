"""Hook domain: extension points and hook callbacks.

This domain handles the registration and emission of hooks
at various execution phases.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.hook.component import IExtensionPoint, IHook

# Common types
from dare_framework3_2.hook.types import HookPhase

# Default implementations
from dare_framework3_2.hook.impl.default_extension_point import DefaultExtensionPoint
from dare_framework3_2.hook.impl.noop_hook import NoopHook

__all__ = [
    # Protocol
    "IExtensionPoint",
    "IHook",
    # Types
    "HookPhase",
    # Implementations
    "DefaultExtensionPoint",
    "NoopHook",
]
