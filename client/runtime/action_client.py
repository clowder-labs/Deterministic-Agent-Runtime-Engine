"""Transport action/control client helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dare_framework.transport import (
    ActionPayload,
    ControlPayload,
    DirectClientChannel,
    EnvelopeKind,
    TransportEnvelope,
    new_envelope_id,
)
from dare_framework.transport.interaction.controls import AgentControl
from dare_framework.transport.interaction.resource_action import ResourceAction


@dataclass(frozen=True)
class ActionClientError(Exception):
    """Raised when transport action/control returns an error payload."""

    code: str
    reason: str
    target: str

    def __str__(self) -> str:
        return f"{self.code}: {self.reason} (target={self.target})"


class TransportActionClient:
    """Thin wrapper around DirectClientChannel ask() for action/control calls."""

    def __init__(self, channel: DirectClientChannel, *, timeout_seconds: float = 30.0) -> None:
        self._channel = channel
        self._timeout = timeout_seconds

    async def invoke_action(
        self,
        action: ResourceAction | str,
        **params: Any,
    ) -> Any:
        action_id = action.value if isinstance(action, ResourceAction) else str(action)
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.ACTION,
            payload=ActionPayload(
                id=new_envelope_id(),
                resource_action=action_id,
                params=dict(params),
            ),
        )
        response = await self._channel.ask(envelope, timeout=self._timeout)
        return _parse_action_response(response.payload, expected_kind="action")

    async def invoke_control(
        self,
        control: AgentControl | str,
        **params: Any,
    ) -> Any:
        control_id = control.value if isinstance(control, AgentControl) else str(control)
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.CONTROL,
            payload=ControlPayload(
                id=new_envelope_id(),
                control_id=control_id,
                params=dict(params),
            ),
        )
        response = await self._channel.ask(envelope, timeout=self._timeout)
        return _parse_action_response(response.payload, expected_kind="control")


def _parse_action_response(payload: Any, *, expected_kind: str) -> Any:
    if expected_kind == "action" and isinstance(payload, ActionPayload):
        if payload.ok is False:
            raise ActionClientError(
                code=str(payload.code or "UNKNOWN_ERROR"),
                reason=str(payload.reason or "unknown transport error"),
                target=str(payload.resource_action or expected_kind),
            )
        return payload.result
    if expected_kind == "control" and isinstance(payload, ControlPayload):
        if payload.ok is False:
            raise ActionClientError(
                code=str(payload.code or "UNKNOWN_ERROR"),
                reason=str(payload.reason or "unknown transport error"),
                target=str(payload.control_id or expected_kind),
            )
        return payload.result
    raise ActionClientError(
        code="INVALID_RESPONSE",
        reason=f"transport response does not match typed {expected_kind} payload contract",
        target=expected_kind,
    )
