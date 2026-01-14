from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
import urllib.error
import urllib.request
from typing import Any, Iterable

from dare_framework.components import BaseComponent, ToolRegistry
from dare_framework.interfaces import IModelAdapter, IPlanGenerator
from dare_framework.models import (
    GenerateOptions,
    Message,
    Milestone,
    MilestoneContext,
    ModelResponse,
    PlanStep,
    ProposedPlan,
    RunContext,
    ToolDefinition,
    new_id,
)

from plan_helpers import DEFAULT_EDIT_TEXT, read_envelope, seen_plan_tool, test_envelope


class OpenAIModelAdapter(BaseComponent, IModelAdapter):
    """Minimal OpenAI adapter using stdlib HTTP to avoid extra dependencies."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = _resolve_base_url(base_url).rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        if _debug_enabled():
            _debug_log(
                "request",
                {
                    "model": self._model,
                    "base_url": self._base_url,
                    "message_count": len(messages),
                    "roles": [msg.role for msg in messages],
                },
            )
        payload = {
            "model": self._model,
            "messages": _serialize_messages(messages),
        }
        if options is not None:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens

        response = await asyncio.to_thread(self._post_json, "/chat/completions", payload)
        if _debug_enabled():
            _debug_log("response", _summarize_response(response))
        content = _pick_message_content(response)
        return ModelResponse(content=content, tool_calls=[])

    async def generate_structured(self, messages: list[Message], output_schema: type) -> Any:
        if _debug_enabled():
            _debug_log(
                "request_structured",
                {
                    "model": self._model,
                    "base_url": self._base_url,
                    "message_count": len(messages),
                },
            )
        payload = {
            "model": self._model,
            "messages": _serialize_messages(messages),
            "response_format": {"type": "json_object"},
        }
        response = await asyncio.to_thread(self._post_json, "/chat/completions", payload)
        if _debug_enabled():
            _debug_log("response_structured", _summarize_response(response))
        content = _pick_message_content(response)
        data = _extract_json(content)
        return _coerce_structured(output_schema, data)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = self._resolve_api_key()
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI request failed: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"OpenAI request failed: {exc.reason} (base_url={self._base_url})"
            ) from exc

    def _resolve_api_key(self) -> str:
        api_key = self._api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIModelAdapter")
        return api_key


class OpenAIPlanGenerator(IPlanGenerator):
    """Plan generator that asks OpenAI for a JSON plan and maps it to PlanStep objects."""

    def __init__(
        self,
        model: IModelAdapter,
        tool_definitions: Iterable[ToolDefinition],
        *,
        plan_tools: Iterable[str] | None = None,
        default_read_path: str = "README.md",
        max_steps: int = 6,
    ) -> None:
        self._model = model
        self._tool_definitions = list(tool_definitions)
        self._tool_names = {tool.name for tool in self._tool_definitions}
        self._plan_tools = set(plan_tools or [])
        self._default_read_path = default_read_path
        self._max_steps = max_steps

    async def generate_plan(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        plan_attempts: list[dict[str, Any]],
        ctx: RunContext,
    ) -> ProposedPlan:
        if _debug_enabled():
            _debug_log(
                "plan_request",
                {
                    "task": milestone.description,
                    "attempt": len(plan_attempts),
                    "reflections": len(milestone_ctx.reflections),
                },
            )
        allowed_plan_tools = [
            tool for tool in self._plan_tools if not seen_plan_tool(milestone_ctx, tool)
        ]
        messages = [
            Message(role="system", content=_plan_system_prompt()),
            Message(
                role="user",
                content=_plan_user_prompt(
                    task=milestone.description,
                    reflections=milestone_ctx.reflections,
                    tool_definitions=self._tool_definitions,
                    plan_tools=allowed_plan_tools,
                    default_read_path=self._default_read_path,
                ),
            ),
        ]
        data = await self._model.generate_structured(messages, output_schema=dict)
        if not isinstance(data, dict):
            data = {}
        if _debug_enabled():
            _debug_log("plan_payload", data)
        steps = self._steps_from_payload(data)
        if _debug_enabled():
            _debug_log(
                "plan_parsed",
                {
                    "plan_description": data.get("plan_description"),
                    "step_count": len(steps),
                    "tools": [step.tool_name for step in steps],
                },
            )
        if not steps:
            steps = [
                PlanStep(
                    step_id=new_id("step"),
                    tool_name="read_file",
                    tool_input={"path": self._default_read_path},
                    envelope=read_envelope(),
                )
            ]
        return ProposedPlan(
            plan_description=str(data.get("plan_description") or milestone.description),
            proposed_steps=steps,
            attempt=len(plan_attempts),
        )

    def _steps_from_payload(self, data: dict[str, Any]) -> list[PlanStep]:
        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, list):
            return []

        steps: list[PlanStep] = []
        for raw_step in raw_steps[: self._max_steps]:
            if not isinstance(raw_step, dict):
                continue
            tool_name = raw_step.get("tool_name") or raw_step.get("tool")
            if not isinstance(tool_name, str):
                continue
            if tool_name not in self._tool_names and tool_name not in self._plan_tools:
                continue
            tool_input = raw_step.get("tool_input") or raw_step.get("input") or {}
            if not isinstance(tool_input, dict):
                tool_input = {}
            if tool_name == "read_file" and "path" not in tool_input:
                tool_input["path"] = self._default_read_path
            if tool_name == "edit_line":
                if "path" not in tool_input:
                    tool_input["path"] = self._default_read_path
                if "line_number" not in tool_input:
                    tool_input["line_number"] = 2
                if "mode" not in tool_input:
                    tool_input["mode"] = "insert"
                if "text" not in tool_input and tool_input.get("mode") == "insert":
                    tool_input["text"] = DEFAULT_EDIT_TEXT
            envelope = None
            if tool_name == "read_file":
                envelope = read_envelope()
            elif tool_name == "run_tests":
                envelope = test_envelope()

            steps.append(
                PlanStep(
                    step_id=new_id("step"),
                    tool_name=tool_name,
                    tool_input=tool_input,
                    description=str(raw_step.get("description") or ""),
                    envelope=envelope,
                )
            )
        return steps


def tool_definitions_from_tools(tools: Iterable[Any]) -> list[ToolDefinition]:
    registry = ToolRegistry()
    registry.register_many(tools)
    return registry.list_tools()


def _serialize_messages(messages: list[Message]) -> list[dict[str, str]]:
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _pick_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "") or ""


def _extract_json(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def _coerce_structured(output_schema: type, data: dict[str, Any] | None) -> Any:
    if data is None:
        return output_schema()
    if hasattr(output_schema, "model_validate"):
        return output_schema.model_validate(data)
    if hasattr(output_schema, "parse_obj"):
        return output_schema.parse_obj(data)
    try:
        return output_schema(**data)
    except Exception:
        return output_schema()


def _plan_system_prompt() -> str:
    return (
        "You are a planning module. Return JSON only, no markdown. "
        "Use the provided tool_name values. Each step must include tool_name and tool_input. "
        "Keep steps minimal and relevant."
    )


def _plan_user_prompt(
    *,
    task: str,
    reflections: list[str],
    tool_definitions: list[ToolDefinition],
    plan_tools: list[str],
    default_read_path: str,
) -> str:
    tool_block = json.dumps(
        [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tool_definitions
        ],
        ensure_ascii=True,
    )
    plan_tools_block = json.dumps(plan_tools, ensure_ascii=True)
    reflections_block = json.dumps(reflections, ensure_ascii=True)
    schema_hint = (
        '{"plan_description": "...", "steps": [{"tool_name": "...", '
        '"tool_input": {}, "description": "..."}]}'
    )
    return (
        f"Task: {task}\n"
        f"Reflections: {reflections_block}\n"
        f"Available tools: {tool_block}\n"
        f"Plan tools (optional): {plan_tools_block}\n"
        f"If you use read_file without a path, default to {default_read_path}.\n"
        "Return JSON with schema:\n"
        f"{schema_hint}"
    )


def _resolve_base_url(base_url: str | None) -> str:
    if base_url:
        return base_url
    env_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    return env_url or "https://api.openai.com/v1"


def _summarize_response(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices", [])
    choice = choices[0] if choices else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    return {
        "id": payload.get("id"),
        "model": payload.get("model"),
        "finish_reason": choice.get("finish_reason"),
        "usage": payload.get("usage", {}),
        "content_preview": (message.get("content") or "")[:120],
    }


def _debug_enabled() -> bool:
    value = os.getenv("OPENAI_DEBUG", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _debug_log(event: str, payload: dict[str, Any]) -> None:
    # Avoid logging secrets; payload is intentionally minimal and sanitized.
    global _DEBUG_SEQ
    _DEBUG_SEQ += 1
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
    print(
        "[openai-debug] "
        f"{timestamp} #{_DEBUG_SEQ} {event}: {json.dumps(payload, ensure_ascii=True)}"
    )


_DEBUG_SEQ = 0
