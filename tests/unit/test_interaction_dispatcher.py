import pytest

from dare_framework.transport import ActionPayload, EnvelopeKind, TransportEnvelope, new_envelope_id
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.dispatcher import ActionHandlerDispatcher
from dare_framework.transport.interaction.handlers import IActionHandler


def _env(*, payload: str) -> TransportEnvelope:
    return TransportEnvelope(
        id=new_envelope_id(),
        kind=EnvelopeKind.ACTION,
        payload=ActionPayload(
            id=new_envelope_id(),
            resource_action=payload,
        ),
    )


class RecordActionHandler(IActionHandler):
    def __init__(self, action_id: ResourceAction, calls: list[str]) -> None:
        self._action_id = action_id
        self._calls = calls

    def supports(self) -> set[ResourceAction]:
        return {self._action_id}

    async def invoke(self, action: ResourceAction, **_params: object):
        self._calls.append(action.value)
        return {"ok": True}


@pytest.mark.asyncio
async def test_action_handler_routing_matches_resource_action() -> None:
    calls: list[str] = []
    dispatcher = ActionHandlerDispatcher()
    dispatcher.register_action_handler(RecordActionHandler(ResourceAction.TOOLS_LIST, calls))
    dispatcher.register_action_handler(RecordActionHandler(ResourceAction.CONFIG_GET, calls))

    tools_result = await dispatcher.handle_action(_env(payload="tools:list"))
    config_result = await dispatcher.handle_action(_env(payload="config:get"))

    assert calls == ["tools:list", "config:get"]
    assert tools_result.ok is True
    assert tools_result.target == "tools:list"
    assert tools_result.resp == {"ok": True}
    assert config_result.ok is True
    assert config_result.target == "config:get"
    assert config_result.resp == {"ok": True}


@pytest.mark.asyncio
async def test_unknown_action_returns_error_result() -> None:
    dispatcher = ActionHandlerDispatcher()

    result = await dispatcher.handle_action(_env(payload="unknown:action"))

    assert result.ok is False
    assert result.target == "unknown:action"
    assert result.code == "UNSUPPORTED_OPERATION"
    assert isinstance(result.reason, str)


@pytest.mark.asyncio
async def test_actions_list_returns_registered_actions() -> None:
    calls: list[str] = []
    dispatcher = ActionHandlerDispatcher()
    dispatcher.register_action_handler(RecordActionHandler(ResourceAction.TOOLS_LIST, calls))
    dispatcher.register_action_handler(RecordActionHandler(ResourceAction.CONFIG_GET, calls))

    result = await dispatcher.handle_action(_env(payload="actions:list"))

    assert result.ok is True
    assert result.target == "actions:list"
    resp = result.resp
    assert isinstance(resp, dict)
    assert sorted(resp.get("actions", [])) == ["actions:list", "config:get", "tools:list"]


@pytest.mark.asyncio
async def test_action_payload_params_must_be_mapping_with_string_keys() -> None:
    dispatcher = ActionHandlerDispatcher()
    malformed_none = TransportEnvelope(
        id=new_envelope_id(),
        kind=EnvelopeKind.ACTION,
        payload=ActionPayload(
            id=new_envelope_id(),
            resource_action="tools:list",
            params=None,  # type: ignore[arg-type]
        ),
    )
    malformed_key = TransportEnvelope(
        id=new_envelope_id(),
        kind=EnvelopeKind.ACTION,
        payload=ActionPayload(
            id=new_envelope_id(),
            resource_action="tools:list",
            params={1: "x"},  # type: ignore[dict-item]
        ),
    )

    none_result = await dispatcher.handle_action(malformed_none)
    key_result = await dispatcher.handle_action(malformed_key)

    assert none_result.ok is False
    assert none_result.code == "INVALID_ACTION_PAYLOAD"
    assert isinstance(none_result.reason, str)
    assert key_result.ok is False
    assert key_result.code == "INVALID_ACTION_PAYLOAD"
    assert isinstance(key_result.reason, str)
