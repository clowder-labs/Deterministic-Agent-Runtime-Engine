"""hook domain facade."""

from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.kernel import IExtensionPoint, IHook, HookFn
from dare_framework.hook._internal.hook_extension_point import HookExtensionPoint
from dare_framework.hook.types import HookDecision, HookEnvelope, HookPhase, HookResult

__all__ = [
    "HookDecision",
    "HookEnvelope",
    "HookFn",
    "HookPhase",
    "HookResult",
    "IExtensionPoint",
    "IHook",
    "IHookManager",
    "HookExtensionPoint",
]
