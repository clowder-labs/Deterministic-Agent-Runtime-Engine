"""Deterministic action dispatcher for transport-driven sessions."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler
from dare_framework.transport.types import EnvelopeKind, TransportEnvelope


@dataclasses.dataclass(frozen=True)
class ActionDispatchResult:
    """Structured action dispatch outcome used by channel response writer."""

    ok: bool
    target: str
    resp: Any | None = None
    code: str | None = None
    reason: str | None = None

    @classmethod
    def success(cls, *, target: str, resp: Any) -> ActionDispatchResult:
        return cls(ok=True, target=target, resp=resp)

    @classmethod
    def error(cls, *, target: str, code: str, reason: str) -> ActionDispatchResult:
        return cls(ok=False, target=target, code=code, reason=reason)


class ActionHandlerDispatcher:
    """Deterministic action router (`ResourceAction -> IActionHandler`)."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger
        self._action_handlers: dict[ResourceAction, IActionHandler] = {}

    def register_action_handler(self, handler: IActionHandler) -> None:
        """Register one handler for each supported `ResourceAction`."""
        for action in handler.supports():
            if action in self._action_handlers:
                raise ValueError(f"duplicate action handler for {action.value!r}")
            self._action_handlers[action] = handler

    async def handle_action(self, envelope: TransportEnvelope) -> ActionDispatchResult:
        """Validate and route action envelope without performing channel write."""
        if envelope.kind != EnvelopeKind.ACTION:
            return ActionDispatchResult.error(
                target="action",
                code="INVALID_ENVELOPE_KIND",
                reason=f"invalid envelope kind for action: {envelope.kind.value!r}",
            )
        raw_action_id = envelope.payload
        if not isinstance(raw_action_id, str):
            return ActionDispatchResult.error(
                target="action",
                code="INVALID_ACTION_PAYLOAD",
                reason="invalid action payload (expected string 'resource:action')",
            )
        return await self._route_action(
            action_id=raw_action_id.strip(),
            params=dict(envelope.meta),
        )

    async def _route_action(
        self,
        *,
        action_id: str,
        params: dict[str, Any],
    ) -> ActionDispatchResult:
        action = ResourceAction.value_of(action_id)
        if action is None:
            return ActionDispatchResult.error(
                target=action_id or "action",
                code="UNSUPPORTED_OPERATION",
                reason=f"invalid action id: {action_id!r}",
            )
        if action == ResourceAction.ACTIONS_LIST:
            return ActionDispatchResult.success(
                target=action.value,
                resp={"actions": self._list_actions()},
            )
        handler = self._action_handlers.get(action)
        if handler is None:
            return ActionDispatchResult.error(
                target=action.value,
                code="UNSUPPORTED_OPERATION",
                reason=f"no handler registered for action {action.value!r}",
            )
        try:
            result = await handler.invoke(action, **params)
        except Exception as exc:
            if self._logger is not None:
                self._logger.exception("action handler invocation failed")
            return ActionDispatchResult.error(
                target=action.value,
                code="ACTION_HANDLER_FAILED",
                reason=f"action handler failed: {exc}",
            )
        return ActionDispatchResult.success(
            target=action.value,
            resp={"result": _jsonify(result)},
        )

    def _list_actions(self) -> list[str]:
        discovered = {action.value for action in self._action_handlers}
        discovered.add(ResourceAction.ACTIONS_LIST.value)
        return sorted(discovered)


def _jsonify(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if dataclasses.is_dataclass(value):
        return _jsonify(dataclasses.asdict(value))
    return str(value)


__all__ = ["ActionDispatchResult", "ActionHandlerDispatcher"]
