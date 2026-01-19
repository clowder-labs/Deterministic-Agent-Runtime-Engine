"""Hook components (Layer 2).

Hooks are loaded via the `dare_framework.v2.hooks` entrypoint group and registered into the
Kernel extension point (`dare_framework.core.hook.IExtensionPoint`).
"""

from dare_framework.components.hooks.noop import NoOpHook
from dare_framework.components.hooks.protocols import IHook

__all__ = [
    "IHook",
    "NoOpHook",
]

