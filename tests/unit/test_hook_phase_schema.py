from dare_framework.hook._internal.phase_schema import schema_for_phase
from dare_framework.hook.types import HookPhase


def test_every_hook_phase_has_schema() -> None:
    for phase in HookPhase:
        schema = schema_for_phase(phase)
        assert "required" in schema
        assert isinstance(schema["required"], tuple)
