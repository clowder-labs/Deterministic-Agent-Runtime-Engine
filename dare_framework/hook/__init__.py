"""hook domain facade."""

from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.kernel import IExtensionPoint, IHook, HookFn
from dare_framework.hook.types import HookPhase

__all__ = ["HookFn", "HookPhase", "IExtensionPoint", "IHook", "IHookManager"]
