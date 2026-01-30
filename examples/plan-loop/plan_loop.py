"""Plan loop example using the canonical dare_framework runtime.

This example wires a deterministic planner + registry validator into
FiveLayerAgent and exercises the Plan -> Execute -> Tool path without
external LLM dependencies.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Add project root to path for local development
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Message
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan import ProposedPlan, ProposedStep
from dare_framework.plan._internal.registry_validator import RegistryPlanValidator
from dare_framework.tool import (
    EchoTool,
    RunContextState,
    ToolManager,
)


def _latest_user_message(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


class EchoPlanner:
    """Deterministic planner that emits a single echo step."""

    def __init__(self, *, capability_id: str) -> None:
        self._attempt = 0
        self.last_plan: ProposedPlan | None = None
        self._capability_id = capability_id

    @property
    def name(self) -> str:
        return "echo_planner"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PLANNER

    async def plan(self, ctx: Any) -> ProposedPlan:
        self._attempt += 1
        message = _latest_user_message(ctx.stm_get())
        if not message:
            message = "hello from planner"

        plan = ProposedPlan(
            plan_description="Echo the latest user message via the echo tool.",
            steps=[
                ProposedStep(
                    step_id=f"step-{self._attempt}",
                    capability_id=self._capability_id,
                    params={"message": message},
                    description="Echo user input.",
                )
            ],
            attempt=self._attempt,
        )
        self.last_plan = plan
        return plan


class DeterministicToolCallModel:
    """Model adapter that issues one tool call, then final text.

    This keeps the example fully offline while still exercising the Tool Loop.
    """

    def __init__(self, *, capability_id: str) -> None:
        self._calls = 0
        self._capability_id = capability_id

    @property
    def name(self) -> str:
        return "deterministic_tool_call_model"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.MODEL_ADAPTER

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        self._calls += 1
        message = _latest_user_message(model_input.messages)

        if self._calls == 1:
            # First response triggers the tool call.
            return ModelResponse(
                content="",
                tool_calls=[
                    {
                        "name": self._capability_id,
                        "capability_id": self._capability_id,
                        "arguments": {"message": message},
                    }
                ],
            )

        # Second response ends the Execute Loop.
        return ModelResponse(
            content=f"Done. Echo tool invoked with: {message}",
            tool_calls=[],
        )


async def main() -> None:
    run_context = RunContextState(config={"workspace_roots": ["."]})

    tool_manager = ToolManager(context_factory=run_context.build)
    descriptor = tool_manager.register_tool(EchoTool())

    planner = EchoPlanner(capability_id=descriptor.id)
    validator = RegistryPlanValidator(tool_gateway=tool_manager)
    model = DeterministicToolCallModel(capability_id=descriptor.id)

    agent = FiveLayerAgent(
        name="plan-loop-demo",
        model=model,
        tools=tool_manager,
        tool_gateway=tool_manager,
        planner=planner,
        validator=validator,
    )

    result = await agent.run("Echo this message through the plan loop.")

    print("Plan:")
    if planner.last_plan is None:
        print("  (no plan generated)")
    else:
        print(f"  description: {planner.last_plan.plan_description}")
        for step in planner.last_plan.steps:
            print(f"  - {step.step_id}: {step.capability_id} {step.params}")

    print("\nRun Result:")
    print(f"  success: {result.success}")
    print(f"  output: {result.output}")
    if result.errors:
        print(f"  errors: {result.errors}")


if __name__ == "__main__":
    asyncio.run(main())
