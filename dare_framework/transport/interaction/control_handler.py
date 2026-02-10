"""Deterministic agent control handler."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from dare_framework.transport.interaction.controls import AgentControl

if TYPE_CHECKING:
    from dare_framework.agent.kernel import IAgent


class AgentControlHandler:
    """Single control handler that maps control values to agent methods."""

    def __init__(self, agent: IAgent) -> None:
        self._agent = agent

    async def invoke(self, control: AgentControl, **params: Any) -> Any:
        # Route controls to lifecycle methods and forward optional keyword params.
        if control == AgentControl.INTERRUPT:
            result = self._agent.interrupt(**params)
        elif control == AgentControl.PAUSE:
            result = self._agent.pause(**params)
        elif control == AgentControl.RETRY:
            result = self._agent.retry(**params)
        elif control == AgentControl.REVERSE:
            result = self._agent.reverse(**params)
        else:  # pragma: no cover - guarded by enum type
            return {"ok": False, "error": f"unsupported control: {control.value}"}
        if inspect.isawaitable(result):
            result = await result
        return {"ok": True, "result": result}

__all__ = ["AgentControlHandler"]
