"""hook domain stable interfaces.

Hooks are intended to be best-effort by default.
"""

from __future__ import annotations

from typing import Any, Callable, Literal, Protocol, runtime_checkable

from dare_framework.hook.types import HookPhase, HookResult
from dare_framework.infra.component import ComponentType, IComponent

HookFn = Callable[[dict[str, Any]], Any]
HookOutcome = HookResult | dict[str, Any] | None


@runtime_checkable
class IHook(IComponent, Protocol):
    """[Component] Hook implementation invoked by the runtime.

    Hooks are best-effort by default; runtimes should treat hook failures as
    non-fatal and continue execution.
    """

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        ...

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookOutcome:
        """[Component] Invoke the hook for a given phase.

        The payload is intentionally unconstrained (phase-specific) so runtimes
        can evolve emission details without locking into a single dict schema.
        """
        ...


class IExtensionPoint(Protocol):
    def register_hook(self, phase: HookPhase, hook: HookFn) -> None: ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> HookResult: ...


__all__ = ["HookFn", "HookOutcome", "IExtensionPoint", "IHook"]
