"""Plan loop example wired to a real model.

References:
- examples/base_tool/tool_chat3.4.py for model/env conventions
- examples/plan-loop/plan_loop.py for deterministic plan loop shape
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
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
from dare_framework.model import OpenAIModelAdapter, Prompt
from dare_framework.plan import ProposedPlan, ProposedStep
from dare_framework.plan._internal.registry_validator import RegistryPlanValidator
from dare_framework.tool import (
    DefaultToolGateway,
    EchoTool,
    GatewayToolProvider,
    NativeToolProvider,
    ReadFileTool,
    RunContextState,
    SearchCodeTool,
)

MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("CHAT_API_KEY", "")
ENDPOINT = os.getenv("CHAT_ENDPOINT", "https://api.openai.com/v1")
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()
WORKSPACE_ROOT = os.getenv("TOOL_WORKSPACE_ROOT", ".")
PLAN_TASK = os.getenv("PLAN_TASK", "Read README.md and summarize the main purpose.")
DEFAULT_READ_PATH = os.getenv("PLAN_DEFAULT_READ_PATH", "README.md")
MAX_STEPS = int(os.getenv("PLAN_MAX_STEPS", "3"))

logger = logging.getLogger("plan-loop-real-model")


def _latest_user_message(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def _tool_catalog(tool_defs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for tool in tool_defs:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        catalog.append(
            {
                "name": name,
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {}),
            }
        )
    return catalog


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output.

    This keeps parsing resilient to code fences or extra text.
    """
    if not text:
        return {}

    cleaned = text.strip()
    if cleaned.startswith("```"):
        fence_end = cleaned.find("```", 3)
        if fence_end != -1:
            cleaned = cleaned[3:fence_end].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start : end + 1]
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {}

    return {}


class JsonPlanPlanner:
    """Planner that asks a real model for a JSON plan."""

    def __init__(
        self,
        model: OpenAIModelAdapter,
        tool_defs: list[dict[str, Any]],
        *,
        default_read_path: str,
        max_steps: int,
    ) -> None:
        self._model = model
        self._tool_defs = list(tool_defs)
        self._tool_names = {tool["name"] for tool in _tool_catalog(self._tool_defs)}
        self._default_read_path = default_read_path
        self._max_steps = max_steps
        self.last_plan: ProposedPlan | None = None

    @property
    def name(self) -> str:
        return "json_plan_planner"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PLANNER

    async def plan(self, ctx: Any) -> ProposedPlan:
        task = _latest_user_message(ctx.stm_get()) or "unknown task"
        tool_catalog = _tool_catalog(self._tool_defs)
        prompt = Prompt(
            messages=[
                Message(
                    role="system",
                    content=(
                        "You are a planning module. Return JSON only (no markdown).\n"
                        "Format: {\"plan_description\": str, \"steps\": "
                        "[{\"tool\": str, \"arguments\": object, \"description\": str}]}\n"
                        "Use only tools from the provided catalog and keep steps <= max_steps."
                    ),
                ),
                Message(
                    role="user",
                    content=(
                        f"Task: {task}\n"
                        f"Default read path: {self._default_read_path}\n"
                        f"max_steps: {self._max_steps}\n"
                        f"Tool catalog: {json.dumps(tool_catalog, ensure_ascii=True)}"
                    ),
                ),
            ],
            tools=[],
            metadata={"purpose": "plan"},
        )

        response = await self._model.generate(prompt)
        data = _extract_json(response.content)
        steps = self._steps_from_payload(data)

        if not steps:
            steps = self._fallback_steps(task)

        plan = ProposedPlan(
            plan_description=str(data.get("plan_description") or task),
            steps=steps,
        )
        self.last_plan = plan
        return plan

    def _steps_from_payload(self, data: dict[str, Any]) -> list[ProposedStep]:
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list):
            return []

        steps: list[ProposedStep] = []
        for idx, raw in enumerate(raw_steps[: self._max_steps], start=1):
            if not isinstance(raw, dict):
                continue
            tool_name = raw.get("tool") or raw.get("tool_name") or raw.get("name")
            if not isinstance(tool_name, str) or tool_name not in self._tool_names:
                continue
            params = raw.get("arguments") or raw.get("params") or raw.get("input") or {}
            if not isinstance(params, dict):
                params = {}
            if tool_name == "read_file" and "path" not in params:
                params["path"] = self._default_read_path

            steps.append(
                ProposedStep(
                    step_id=f"step-{idx}",
                    capability_id=f"tool:{tool_name}",
                    params=params,
                    description=str(raw.get("description") or ""),
                )
            )

        return steps

    def _fallback_steps(self, task: str) -> list[ProposedStep]:
        if "read_file" in self._tool_names:
            return [
                ProposedStep(
                    step_id="step-1",
                    capability_id="tool:read_file",
                    params={"path": self._default_read_path},
                    description="Fallback to read the default file.",
                )
            ]
        if "echo" in self._tool_names:
            return [
                ProposedStep(
                    step_id="step-1",
                    capability_id="tool:echo",
                    params={"message": task},
                    description="Fallback to echo the task.",
                )
            ]
        return []


async def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "boot plan loop (real model)",
        extra={
            "model": MODEL,
            "endpoint": ENDPOINT,
            "api_key_set": bool(API_KEY),
            "workspace_root": WORKSPACE_ROOT,
        },
    )

    model = OpenAIModelAdapter(
        model=MODEL,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        http_client_options=HTTP_CLIENT_OPTIONS,
    )

    run_context = RunContextState(
        config={
            "workspace_roots": [WORKSPACE_ROOT],
            "tools": {
                "read_file": {"max_bytes": 1_000_000},
                "search_code": {
                    "max_results": 50,
                    "max_file_bytes": 1_000_000,
                    "ignore_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv"],
                },
            },
        }
    )

    tools = [ReadFileTool(), SearchCodeTool(), EchoTool()]
    gateway = DefaultToolGateway()
    gateway.register_provider(NativeToolProvider(tools=tools, context_factory=run_context.build))

    tool_provider = GatewayToolProvider(gateway)
    await tool_provider.refresh()

    planner = JsonPlanPlanner(
        model,
        tool_provider.list_tools(),
        default_read_path=DEFAULT_READ_PATH,
        max_steps=MAX_STEPS,
    )
    validator = RegistryPlanValidator(tool_gateway=gateway)

    agent = FiveLayerAgent(
        name="plan-loop-real-model",
        model=model,
        tools=tool_provider,
        tool_gateway=gateway,
        planner=planner,
        validator=validator,
    )

    result = await agent.run(PLAN_TASK)

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
