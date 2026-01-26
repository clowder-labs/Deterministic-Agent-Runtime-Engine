from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
import urllib.error
import urllib.request
from typing import Any, Iterable

from dare_framework.builder.base_component import BaseComponent
from dare_framework.contracts.ids import generator_id
from dare_framework.model.components import IModelAdapter
from dare_framework.model.types import GenerateOptions, Message, ModelResponse
from dare_framework.contracts.tool import ITool, ToolDefinition
from dare_framework.context.types import AssembledContext
from dare_framework.plan.planning import ProposedPlan, ProposedStep
from dare_framework.plan.components import IPlanner

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
                    "tool_count": len(tools or []),
                },
            )
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": _serialize_messages(messages),
        }
        if tools:
            payload["tools"] = _serialize_tools(tools)
        if options is not None:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens

        response = await asyncio.to_thread(self._post_json, "/chat/completions", payload)
        if _debug_enabled():
            _debug_log("response", _summarize_response(response))
        content = _pick_message_content(response)
        allowed_tools = {tool.name for tool in tools} if tools else None
        tool_calls = _extract_tool_calls(response, allowed_tools)
        return ModelResponse(content=content, tool_calls=tool_calls)

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
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self._extra_headers())
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            headers=headers,
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
        api_key = self._api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY or OPENROUTER_API_KEY is required for OpenAIModelAdapter"
            )
        return api_key

    def _extra_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        referer = os.getenv("OPENROUTER_HTTP_REFERER") or os.getenv("OPENROUTER_REFERER")
        title = os.getenv("OPENROUTER_APP_TITLE") or os.getenv("OPENROUTER_TITLE")
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title
        return headers


class OpenAIPlanner(IPlanner):
    """Planner that asks OpenAI for a JSON plan and maps it to ProposedStep objects."""

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

    async def plan(self, ctx: AssembledContext) -> ProposedPlan:
        task = _last_user_message(ctx) or "unknown task"
        reflections: list[str] = []
        if _debug_enabled():
            _debug_log(
                "plan_request",
                {
                    "task": task,
                    "reflections": len(reflections),
                },
            )
        allowed_plan_tools = [
            tool for tool in self._plan_tools if not seen_plan_tool(reflections, tool)
        ]
        messages = [
            Message(role="system", content=_plan_system_prompt()),
            Message(
                role="user",
                content=_plan_user_prompt(
                    task=task,
                    reflections=reflections,
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
                    "tools": [step.capability_id for step in steps],
                },
            )
        if not steps:
            steps = [
                ProposedStep(
                    step_id=generator_id("step"),
                    capability_id="tool:read_file",
                    params={"path": self._default_read_path},
                    envelope=read_envelope(),
                )
            ]
        return ProposedPlan(
            plan_description=str(data.get("plan_description") or task),
            steps=steps,
        )

    def _steps_from_payload(self, data: dict[str, Any]) -> list[ProposedStep]:
        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, list):
            return []

        steps: list[ProposedStep] = []
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

            capability_id = f"plan:{tool_name}" if tool_name in self._plan_tools else f"tool:{tool_name}"
            steps.append(
                ProposedStep(
                    step_id=generator_id("step"),
                    capability_id=capability_id,
                    params=tool_input,
                    description=str(raw_step.get("description") or ""),
                    envelope=envelope,
                )
            )
        return steps


def tool_definitions_from_tools(tools: Iterable[Any]) -> list[ToolDefinition]:
    """Build ToolDefinition metadata from in-process ITool objects."""

    definitions: list[ToolDefinition] = []
    for tool in tools:
        if not isinstance(tool, ITool):
            continue
        definitions.append(
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=dict(tool.input_schema),
                output_schema=dict(tool.output_schema),
                tool_type=tool.tool_type,
                risk_level=tool.risk_level,
                requires_approval=tool.requires_approval,
                timeout_seconds=tool.timeout_seconds,
                produces_assertions=list(tool.produces_assertions),
                is_work_unit=tool.is_work_unit,
            )
        )
    return definitions


def _last_user_message(ctx: AssembledContext) -> str | None:
    for msg in reversed(ctx.messages):
        if msg.role == "user" and msg.content:
            return msg.content
    return None


def _serialize_messages(messages: list[Message]) -> list[dict[str, Any]]:
    serialized = []
    for msg in messages:
        item: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.name and msg.role != "tool":
            item["name"] = msg.name
        if msg.tool_call_id:
            item["tool_call_id"] = msg.tool_call_id
        if msg.tool_calls and msg.role == "assistant":
            item["tool_calls"] = _serialize_tool_calls(msg.tool_calls)
        serialized.append(item)
    return serialized


def _serialize_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized = []
    for idx, call in enumerate(tool_calls):
        if not isinstance(call, dict):
            continue
        name = call.get("name")
        if not name:
            continue
        arguments = call.get("arguments", {})
        if not isinstance(arguments, str):
            try:
                arguments = json.dumps(arguments, ensure_ascii=True)
            except TypeError:
                arguments = json.dumps({"raw": str(arguments)}, ensure_ascii=True)
        serialized.append(
            {
                "id": call.get("id") or f"call_{idx}",
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        )
    return serialized


def _serialize_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [_tool_definition(tool) for tool in tools]


def _tool_definition(tool: ToolDefinition) -> dict[str, Any]:
    parameters = tool.input_schema or {"type": "object", "properties": {}}
    if "type" not in parameters:
        parameters = {"type": "object", "properties": parameters}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        },
    }


def _pick_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "") or ""


def _extract_tool_calls(
    payload: dict[str, Any],
    allowed_tools: set[str] | None = None,
) -> list[dict[str, Any]]:
    choices = payload.get("choices", [])
    choice = choices[0] if choices else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    raw_calls = message.get("tool_calls") or []
    if not isinstance(raw_calls, list):
        return []
    tool_calls = []
    dropped = []
    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") if isinstance(call.get("function"), dict) else {}
        name = fn.get("name") or call.get("name")
        if not name:
            continue
        if allowed_tools is not None and name not in allowed_tools:
            dropped.append(name)
            continue
        arguments = fn.get("arguments") if fn else call.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = arguments
        elif arguments is None:
            arguments = {}
        tool_calls.append(
            {
                "id": call.get("id"),
                "name": name,
                "arguments": arguments,
            }
        )
    if dropped and _debug_enabled():
        _debug_log("tool_calls_dropped", {"names": dropped})
    return tool_calls


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
    tool_calls = message.get("tool_calls") or []
    tool_call_count = len(tool_calls) if isinstance(tool_calls, list) else 0
    tool_call_names = []
    if isinstance(tool_calls, list):
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = fn.get("name") or call.get("name")
            if name:
                tool_call_names.append(name)
    return {
        "id": payload.get("id"),
        "model": payload.get("model"),
        "finish_reason": choice.get("finish_reason"),
        "usage": payload.get("usage", {}),
        "content_preview": (message.get("content") or "")[:120],
        "tool_call_count": tool_call_count,
        "tool_call_names": tool_call_names[:5],
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
