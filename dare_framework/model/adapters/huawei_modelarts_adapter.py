"""Huawei ModelArts model adapter using OpenAI SDK-compatible chat completions."""

from __future__ import annotations

import json
import os
from typing import Any

from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse

_MODELARTS_BASE_URL = "https://api.modelarts-maas.com/v2"


class HuaweiModelArtsModelAdapter(IModelAdapter):
    """Model adapter for Huawei ModelArts MaaS (OpenAI-compatible)."""

    def __init__(
        self,
        *,
        name: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        http_client_options: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._name = name or "huawei-modelarts"
        self._api_key = api_key or os.getenv("HUAWEI_MODELARTS_API_KEY")
        self._model = model
        self._base_url = base_url or os.getenv("HUAWEI_MODELARTS_BASE_URL") or _MODELARTS_BASE_URL
        self._http_client_options = dict(http_client_options or {})
        self._extra = dict(extra or {})
        self._client: Any = None

        if not self._api_key:
            raise ValueError(
                "Huawei ModelArts API key is required. Set HUAWEI_MODELARTS_API_KEY environment variable."
            )
        if not self._model:
            raise ValueError("Huawei ModelArts model is required. Set llm.model in config or pass --model.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model or ""

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        client = self._ensure_client()
        messages = _serialize_messages(model_input.messages)

        api_params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if model_input.tools:
            api_params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in model_input.tools
            ]

        if self._extra:
            api_params.update(self._extra)
        if options is not None:
            if options.temperature is not None:
                api_params["temperature"] = options.temperature
            if options.max_tokens is not None:
                api_params["max_tokens"] = options.max_tokens
            if options.top_p is not None:
                api_params["top_p"] = options.top_p
            if options.stop is not None:
                api_params["stop"] = options.stop

        response = await client.chat.completions.create(**api_params)
        message = response.choices[0].message
        content = message.content or ""
        tool_calls = _extract_tool_calls(message)
        thinking_content = _extract_thinking_content(message)

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        reasoning_tokens = _extract_reasoning_tokens(response)
        if reasoning_tokens is not None:
            if usage is None:
                usage = {}
            usage["reasoning_tokens"] = reasoning_tokens

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            thinking_content=thinking_content,
            metadata={
                "model": self.model,
                "finish_reason": response.choices[0].finish_reason,
                "base_url": self._base_url,
            },
        )

    def _ensure_client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "OpenAI SDK is required for Huawei ModelArts. Install with: pip install openai"
            ) from exc

        client_kwargs: dict[str, Any] = {
            "api_key": self._api_key,
            "base_url": self._base_url,
        }

        http_client = _build_async_http_client(self._http_client_options)
        if http_client is not None:
            client_kwargs["http_client"] = http_client

        return AsyncOpenAI(**client_kwargs)


def _serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for msg in messages:
        role = str(getattr(msg, "role", "user"))
        payload: dict[str, Any] = {
            "role": role,
            "content": _serialize_openai_compatible_content(msg),
        }
        if role == "assistant":
            tool_calls = _normalize_tool_calls_for_openai_sdk(_extract_message_tool_calls(msg))
            if tool_calls:
                payload["tool_calls"] = tool_calls
        tool_call_id = _extract_message_tool_call_id(msg)
        name = getattr(msg, "name", None)
        if role == "tool" and tool_call_id:
            payload["tool_call_id"] = tool_call_id
        elif name:
            payload["name"] = name
        serialized.append(payload)
    return serialized


def _serialize_openai_compatible_content(message: Any) -> Any:
    text = _message_text(message)
    attachments = list(getattr(message, "attachments", []) or [])
    if not attachments:
        return text

    content: list[dict[str, Any]] = []
    if text:
        content.append({"type": "text", "text": text})
    for attachment in attachments:
        if str(getattr(attachment, "kind", "")).strip().lower() != "image":
            raise ValueError("unsupported attachment kind for Huawei ModelArts serialization")
        content.append({"type": "image_url", "image_url": {"url": attachment.uri}})
    return content


def _message_text(message: Any) -> str:
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    return ""


def _extract_message_tool_calls(message: Any) -> Any:
    data = getattr(message, "data", None)
    if isinstance(data, dict) and isinstance(data.get("tool_calls"), list):
        return data["tool_calls"]
    return []


def _extract_message_tool_call_id(message: Any) -> str | None:
    data = getattr(message, "data", None)
    if isinstance(data, dict):
        tool_call_id = data.get("tool_call_id")
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            return tool_call_id
    name = getattr(message, "name", None)
    if isinstance(name, str) and name.strip():
        return name
    return None


def _normalize_tool_calls_for_openai_sdk(tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_calls, list):
        return []

    normalized: list[dict[str, Any]] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        name = call.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        raw_args = call.get("arguments", call.get("args", {}))
        if isinstance(raw_args, str):
            args_json = raw_args
        else:
            safe_args = raw_args if isinstance(raw_args, dict) else {}
            args_json = json.dumps(safe_args, ensure_ascii=False)

        normalized_call: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": name,
                "arguments": args_json,
            },
        }
        call_id = call.get("id") or call.get("tool_call_id")
        if isinstance(call_id, str) and call_id.strip():
            normalized_call["id"] = call_id
        normalized.append(normalized_call)
    return normalized


def _extract_tool_calls(message: Any) -> list[dict[str, Any]]:
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return []

    normalized: list[dict[str, Any]] = []
    for call in tool_calls:
        try:
            name = call.function.name
            arguments_raw = call.function.arguments
            try:
                arguments = json.loads(arguments_raw) if arguments_raw else {}
            except json.JSONDecodeError:
                arguments = {"raw": arguments_raw}
            normalized.append(
                {
                    "id": getattr(call, "id", None),
                    "name": name,
                    "arguments": arguments,
                }
            )
        except AttributeError:
            continue
    return normalized


def _build_async_http_client(options: dict[str, Any]) -> Any | None:
    if not options:
        return None
    try:
        import httpx
    except Exception:
        return None
    try:
        return httpx.AsyncClient(**options)
    except Exception:
        return None


def _extract_thinking_content(message: Any) -> str | None:
    for attr in ("reasoning_content", "reasoning", "thinking"):
        text = _coerce_text(getattr(message, attr, None))
        if text:
            return text

    additional_kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        for key in ("reasoning_content", "reasoning", "thinking"):
            text = _coerce_text(additional_kwargs.get(key))
            if text:
                return text

    model_extra = getattr(message, "model_extra", None)
    if isinstance(model_extra, dict):
        for key in ("reasoning_content", "reasoning", "thinking"):
            text = _coerce_text(model_extra.get(key))
            if text:
                return text
    return None


def _extract_reasoning_tokens(response: Any) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    candidates: list[Any] = [
        getattr(usage, "reasoning_tokens", None),
        _get_nested_value(getattr(usage, "completion_tokens_details", None), "reasoning_tokens"),
        _get_nested_value(getattr(usage, "output_tokens_details", None), "reasoning_tokens"),
        _get_nested_value(getattr(usage, "output_tokens_details", None), "reasoning"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _get_nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        for key in ("text", "content", "reasoning", "thinking"):
            text = _coerce_text(value.get(key))
            if text:
                return text
        return None
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _coerce_text(item)
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
    return None


__all__ = ["HuaweiModelArtsModelAdapter"]
