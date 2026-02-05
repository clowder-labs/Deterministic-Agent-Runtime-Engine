"""OpenRouter model adapter using OpenAI SDK."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse


class OpenRouterModelAdapter(IModelAdapter):
    """Model adapter for OpenRouter API (OpenAI-compatible)."""

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
        self._name = name or "openrouter"
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._model = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
        self._base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self._http_client_options = dict(http_client_options or {})
        self._extra = dict(extra or {})
        self._client: Any = None

        if not self._api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")

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
        messages = _serialize_messages(model_input.messages)

        api_params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }
        if model_input.tools:
            api_params["tools"] = model_input.tools

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

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            metadata={
                "model": self._model,
                "finish_reason": response.choices[0].finish_reason,
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
                "OpenAI SDK is required for OpenRouter. Install with: pip install openai"
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
        payload: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.role == "tool" and msg.name:
            payload["tool_call_id"] = msg.name
        elif msg.name:
            payload["name"] = msg.name
        serialized.append(payload)
    return serialized


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
            normalized.append({
                "id": getattr(call, "id", None),
                "name": name,
                "arguments": arguments,
            })
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


__all__ = ["OpenRouterModelAdapter"]
