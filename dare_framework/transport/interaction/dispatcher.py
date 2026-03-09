"""Deterministic action dispatcher for transport-driven sessions."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Mapping

from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler
from dare_framework.transport.types import ActionPayload, EnvelopeKind, TransportEnvelope


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
        payload = envelope.payload
        if not isinstance(payload, ActionPayload):
            return ActionDispatchResult.error(
                target="action",
                code="INVALID_ACTION_PAYLOAD",
                reason="invalid action payload (expected ActionPayload)",
            )
        params = _coerce_action_params(payload.params)
        if params is None:
            return ActionDispatchResult.error(
                target="action",
                code="INVALID_ACTION_PAYLOAD",
                reason="invalid action payload params (expected mapping with string keys)",
            )
        params.update(envelope.meta)
        action_id = payload.resource_action.strip()
        if not action_id:
            return ActionDispatchResult.error(
                target="action",
                code="INVALID_ACTION_PAYLOAD",
                reason="invalid action payload (missing resource_action)",
            )
        return await self._route_action(
            action_id=action_id,
            params=params,
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
            resp=_jsonify(result),
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


def _coerce_action_params(params: Any) -> dict[str, Any] | None:
    if not isinstance(params, Mapping):
        return None
    normalized: dict[str, Any] = {}
    for key, value in params.items():
        if not isinstance(key, str):
            return None
        normalized[key] = value
    return normalized


__all__ = ["ActionDispatchResult", "ActionHandlerDispatcher"]
