import pytest

from dare_framework.component_manager import ComponentDiscoveryConfig, ComponentManager
from dare_framework.components.base_component import BaseComponent
from dare_framework.core.interfaces import IValidator
from dare_framework.core.models import Milestone, ProposedStep, RunContext, ValidationResult, VerifyResult


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


class RecordingValidator(BaseComponent, IValidator):
    def __init__(self, name: str, order: int, log: list[str]):
        self._name = name
        self._order = order
        self._log = log

    @property
    def order(self) -> int:
        return self._order

    async def init(self, config=None, prompts=None) -> None:
        self._log.append(f"init:{self._name}")

    def register(self, registrar) -> None:
        self._log.append(f"register:{self._name}")
        registrar.register_component(self)

    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        return ValidationResult(success=True, errors=[])

    async def validate_milestone(self, milestone: Milestone, result, ctx: RunContext) -> VerifyResult:
        return VerifyResult(success=True, errors=[], evidence=[])

    async def validate_evidence(self, evidence, predicate) -> bool:
        return True


@pytest.mark.asyncio
async def test_component_manager_orders_init_and_register():
    log: list[str] = []

    def low_factory():
        return RecordingValidator("low", 10, log)

    def high_factory():
        return RecordingValidator("high", 50, log)

    entry_points = FakeEntryPoints(
        {
            "dare_framework.validators": [
                FakeEntryPoint("low", low_factory),
                FakeEntryPoint("high", high_factory),
            ]
        }
    )
    config = ComponentDiscoveryConfig(
        enabled=True,
        groups={"validators": "dare_framework.validators"},
    )
    manager = ComponentManager(
        discovery_config=config,
        entry_points_loader=lambda: entry_points,
    )

    await manager.load()

    assert log == ["init:low", "register:low", "init:high", "register:high"]


@pytest.mark.asyncio
async def test_component_manager_filters_entry_points():
    log: list[str] = []

    def keep_factory():
        return RecordingValidator("keep", 10, log)

    def skip_factory():
        return RecordingValidator("skip", 20, log)

    entry_points = FakeEntryPoints(
        {
            "dare_framework.validators": [
                FakeEntryPoint("keep", keep_factory),
                FakeEntryPoint("skip", skip_factory),
            ]
        }
    )
    config = ComponentDiscoveryConfig(
        enabled=True,
        groups={"validators": "dare_framework.validators"},
        include={"keep"},
    )
    manager = ComponentManager(
        discovery_config=config,
        entry_points_loader=lambda: entry_points,
    )

    await manager.load()

    assert log == ["init:keep", "register:keep"]


@pytest.mark.asyncio
async def test_component_manager_lifecycle_ownership():
    closed: list[str] = []

    class ClosingValidator(RecordingValidator):
        async def close(self) -> None:
            closed.append(self._name)

    def owned_factory():
        return ClosingValidator("owned", 10, [])

    entry_points = FakeEntryPoints(
        {"dare_framework.validators": [FakeEntryPoint("owned", owned_factory)]}
    )
    config = ComponentDiscoveryConfig(
        enabled=True,
        groups={"validators": "dare_framework.validators"},
    )
    manager = ComponentManager(
        discovery_config=config,
        entry_points_loader=lambda: entry_points,
    )

    external = ClosingValidator("external", 10, [])
    manager.add_component(external)

    await manager.load()
    await manager.close()

    assert closed == ["owned"]
