from dare_framework.hook.types import HookDecision, HookEnvelope, HookResult


def test_hook_contract_types_exist() -> None:
    envelope = HookEnvelope(
        hook_version=1,
        phase="before_tool",
        invocation_id="id-1",
        context_id="ctx-1",
        timestamp_ms=1,
        payload={},
    )
    result = HookResult(decision=HookDecision.ALLOW)
    assert envelope.hook_version == 1
    assert result.decision.value == "allow"
