"""Anthropic model adapter using the official anthropic SDK."""

from __future__ import annotations

import json
import os
from typing import Any

from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse


class AnthropicModelAdapter(IModelAdapter):
    """Model adapter for Anthropic Messages API."""

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
        self._name = name or "anthropic"
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._model = _resolve_model_name(model=model, env_model=os.getenv("ANTHROPIC_MODEL"))
        self._base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self._http_client_options = dict(http_client_options or {})
        self._extra = dict(extra or {})
        self._client: Any = None

        if not self._api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        client = self._ensure_client()
        system_prompt, messages = _serialize_system_and_messages(model_input.messages)

        params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": _resolve_max_tokens(options=options, extra=self._extra),
        }
        if system_prompt:
            params["system"] = system_prompt
        if model_input.tools:
            params["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in model_input.tools
            ]

        if self._extra:
            extra_params = dict(self._extra)
            # Keep normalized max_tokens from _resolve_max_tokens/options; raw extra values
            # like None/"128" should not override it after merge.
            extra_params.pop("max_tokens", None)
            params.update(extra_params)
        if options is not None:
            if options.temperature is not None:
                params["temperature"] = options.temperature
            if options.max_tokens is not None:
                params["max_tokens"] = options.max_tokens
            if options.top_p is not None:
                params["top_p"] = options.top_p
            if options.stop is not None:
                params["stop_sequences"] = options.stop

        response = await client.messages.create(**params)
        content_blocks = list(getattr(response, "content", []) or [])

        return ModelResponse(
            content=_extract_response_text(content_blocks),
            tool_calls=_extract_tool_calls(content_blocks),
            usage=_extract_usage(getattr(response, "usage", None)),
            thinking_content=_extract_thinking_content(content_blocks),
            metadata={
                "model": self._model,
                "stop_reason": getattr(response, "stop_reason", None),
            },
        )

    def _ensure_client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> Any:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic SDK is required for AnthropicModelAdapter. Install with: pip install anthropic"
            ) from exc

        client_kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        http_client = _build_async_http_client(self._http_client_options)
        if http_client is not None:
            client_kwargs["http_client"] = http_client

        return AsyncAnthropic(**client_kwargs)


def _resolve_model_name(*, model: str | None, env_model: str | None) -> str:
    selected = model or env_model
    if not selected or not selected.strip():
        raise ValueError(
            "Anthropic model is required. Set Config.llm.model or ANTHROPIC_MODEL environment variable."
        )
    return selected.strip()


def _resolve_max_tokens(*, options: GenerateOptions | None, extra: dict[str, Any]) -> int:
    if options is not None and options.max_tokens is not None:
        return int(options.max_tokens)
    extra_value = extra.get("max_tokens")
    if extra_value is not None:
        return int(extra_value)
    env_value = os.getenv("ANTHROPIC_MAX_TOKENS")
    if env_value is not None:
        try:
            return int(env_value)
        except ValueError:
            pass
    return 2048


def _serialize_system_and_messages(messages: list[Any]) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    payload: list[dict[str, Any]] = []

    for msg in messages:
        role = str(getattr(msg, "role", "user"))
        content = _message_text(msg)
        if role == "system":
            text = content.strip()
            if text:
                system_parts.append(text)
            continue

        if role == "assistant":
            message_content: list[dict[str, Any]] = []
            if content:
                message_content.append({"type": "text", "text": content})
            message_content.extend(_serialize_image_attachments(msg))
            tool_calls = _normalize_tool_calls(_extract_message_tool_calls(msg))
            message_content.extend(tool_calls)
            if not message_content:
                message_content.append({"type": "text", "text": ""})
            payload.append({"role": "assistant", "content": message_content})
            continue

        if role == "tool":
            tool_call_id = _extract_message_tool_call_id(msg) or "tool_call"
            payload.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": content,
                        }
                    ],
                }
            )
            continue

        user_attachments = _serialize_image_attachments(msg)
        if not user_attachments:
            payload.append({"role": "user", "content": content})
            continue

        user_content: list[dict[str, Any]] = []
        if content:
            user_content.append({"type": "text", "text": content})
        user_content.extend(user_attachments)
        payload.append({"role": "user", "content": user_content})

    system_prompt = "\n\n".join(system_parts) if system_parts else None
    return system_prompt, payload


def _normalize_tool_calls(tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_calls, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, call in enumerate(tool_calls):
        if not isinstance(call, dict):
            continue
        call_id = call.get("id") or call.get("tool_call_id") or f"toolu_{index + 1}"
        name = call.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        arguments = call.get("arguments", call.get("args", {}))
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"raw": arguments}
        if not isinstance(arguments, dict):
            arguments = {}
        normalized.append(
            {
                "type": "tool_use",
                "id": str(call_id),
                "name": name,
                "input": arguments,
            }
        )
    return normalized


def _serialize_image_attachments(message: Any) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for attachment in list(getattr(message, "attachments", []) or []):
        if str(getattr(attachment, "kind", "")).strip().lower() != "image":
            raise ValueError("unsupported attachment kind for Anthropic serialization")
        inline_block = _serialize_inline_image_attachment(attachment)
        if inline_block is not None:
            blocks.append(inline_block)
            continue
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "url",
                    "url": attachment.uri,
                },
            }
        )
    return blocks


def _serialize_inline_image_attachment(attachment: Any) -> dict[str, Any] | None:
    uri = getattr(attachment, "uri", None)
    if not isinstance(uri, str) or not uri.startswith("data:"):
        return None
    header, _, encoded = uri.partition(",")
    if not header or not encoded or ";base64" not in header:
        raise ValueError("unsupported data URI image for Anthropic serialization")
    media_type = header[5:].split(";", 1)[0].strip()
    if not media_type:
        media_type = str(getattr(attachment, "mime_type", "") or "").strip() or "application/octet-stream"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": encoded,
        },
    }


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


def _extract_response_text(content_blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        if _block_type(block) != "text":
            continue
        text = _coerce_text(_block_value(block, "text"))
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_thinking_content(content_blocks: list[Any]) -> str | None:
    parts: list[str] = []
    for block in content_blocks:
        if _block_type(block) not in {"thinking", "reasoning"}:
            continue
        text = (
            _coerce_text(_block_value(block, "thinking"))
            or _coerce_text(_block_value(block, "reasoning"))
            or _coerce_text(_block_value(block, "text"))
            or _coerce_text(_block_value(block, "content"))
        )
        if text:
            parts.append(text)
    if not parts:
        return None
    return "\n".join(parts)


def _extract_tool_calls(content_blocks: list[Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for block in content_blocks:
        if _block_type(block) != "tool_use":
            continue
        call_id = _block_value(block, "id")
        name = _block_value(block, "name")
        if not isinstance(name, str) or not name.strip():
            continue
        arguments = _block_value(block, "input")
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append(
            {
                "id": str(call_id) if call_id is not None else None,
                "name": name,
                "arguments": arguments,
            }
        )
    return calls


def _extract_usage(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None

    prompt_tokens = _to_int(_get_nested_value(usage, "input_tokens"))
    completion_tokens = _to_int(_get_nested_value(usage, "output_tokens"))
    total_tokens = (
        prompt_tokens + completion_tokens
        if prompt_tokens is not None and completion_tokens is not None
        else _to_int(_get_nested_value(usage, "total_tokens"))
    )

    payload: dict[str, Any] = {}
    if prompt_tokens is not None:
        payload["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        payload["completion_tokens"] = completion_tokens
    if total_tokens is not None:
        payload["total_tokens"] = total_tokens

    reasoning_tokens = _extract_reasoning_tokens(usage)
    if reasoning_tokens is not None:
        payload["reasoning_tokens"] = reasoning_tokens

    if not payload:
        return None
    return payload


def _extract_reasoning_tokens(usage: Any) -> int | None:
    candidates = [
        _get_nested_value(usage, "reasoning_tokens"),
        _get_nested_value(_get_nested_value(usage, "output_tokens_details"), "reasoning_tokens"),
        _get_nested_value(_get_nested_value(usage, "output_tokens_details"), "thinking_tokens"),
        _get_nested_value(_get_nested_value(usage, "completion_tokens_details"), "reasoning_tokens"),
    ]
    for candidate in candidates:
        value = _to_int(candidate)
        if value is not None:
            return value
    return None


def _block_type(block: Any) -> str | None:
    if isinstance(block, dict):
        value = block.get("type")
    else:
        value = getattr(block, "type", None)
    return str(value) if value is not None else None


def _block_value(block: Any, key: str) -> Any:
    if isinstance(block, dict):
        return block.get(key)
    return getattr(block, key, None)


def _get_nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        for key in ("text", "content", "thinking", "reasoning"):
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


__all__ = [
    "AnthropicModelAdapter",
    "_extract_response_text",
    "_extract_thinking_content",
    "_extract_tool_calls",
    "_extract_usage",
    "_resolve_model_name",
    "_serialize_system_and_messages",
]
