import pytest

from dare_framework.builder import AgentBuilder
from dare_framework.component_manager import ENTRYPOINT_MODEL_ADAPTERS, ENTRYPOINT_VALIDATORS
from dare_framework.components.validator import CompositeValidator
from dare_framework.components.base_component import BaseComponent
from dare_framework.core.interfaces import IModelAdapter, IValidator
from dare_framework.core.models import (
    Milestone,
    ModelResponse,
    ProposedStep,
    RunContext,
    ValidationResult,
    VerifyResult,
    new_id,
)
from dare_framework import component_manager


class FakeEntryPoint:
    def __init__(self, name, loader):
        self.name = name
        self._loader = loader

    def load(self):
        return self._loader


class FakeEntryPoints:
    def __init__(self, mapping):
        self._mapping = mapping

    def select(self, group=None):
        return list(self._mapping.get(group, []))


class FailingValidator(BaseComponent, IValidator):
    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        return ValidationResult(success=False, errors=["fail"])

    async def validate_milestone(self, milestone: Milestone, result, ctx: RunContext) -> VerifyResult:
        return VerifyResult(success=False, errors=["fail"], evidence=[])

    async def validate_evidence(self, evidence, predicate) -> bool:
        return False


class StubAdapter(BaseComponent, IModelAdapter):
    async def generate(self, messages, tools=None, options=None) -> ModelResponse:
        return ModelResponse(content="ok", tool_calls=[])

    async def generate_structured(self, messages, output_schema):
        return output_schema()


@pytest.mark.asyncio
async def test_builder_loads_discovered_components(monkeypatch):
    entry_points = FakeEntryPoints(
        {
            ENTRYPOINT_VALIDATORS: [FakeEntryPoint("validator", FailingValidator)],
            ENTRYPOINT_MODEL_ADAPTERS: [FakeEntryPoint("adapter", StubAdapter)],
        }
    )
    monkeypatch.setattr(component_manager.metadata, "entry_points", lambda: entry_points)

    builder = AgentBuilder("test")
    await builder._load_components()

    assert isinstance(builder._validator, CompositeValidator)
    assert isinstance(builder._model_adapter, StubAdapter)

    result = await builder._validator.validate_plan(
        [ProposedStep(step_id=new_id("step"), tool_name="noop", tool_input={})],
        RunContext(deps=None, run_id="run"),
    )
    assert result.success is False
    assert result.errors == ["fail"]
