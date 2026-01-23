"""hook domain facade."""

from dare_framework3_4.hook.kernel import IExtensionPoint, HookFn
from dare_framework3_4.hook.types import HookPhase

__all__ = ["HookFn", "HookPhase", "IExtensionPoint"]
