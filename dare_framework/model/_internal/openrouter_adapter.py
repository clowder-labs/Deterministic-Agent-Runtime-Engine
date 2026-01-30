"""OpenRouter model adapter using OpenAI SDK (IModelAdapter)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal

from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import GenerateOptions, ModelInput, ModelResponse

# Lazy import to avoid dependency if not using OpenRouter
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore[misc, assignment]


class OpenRouterModelAdapter(IModelAdapter):
    """Model adapter for OpenRouter API (OpenAI SDK compatible).

    Requires the `openai` package. Configure via env: OPENROUTER_API_KEY,
    OPENROUTER_MODEL, OPENROUTER_BASE_URL.

    Args:
        name: Adapter name for config lookups (default "openrouter").
        model: Model name (e.g. "qwen/qwen3-coder:free").
        api_key: OpenRouter API key.
        endpoint: API base URL (defaults to OpenRouter production).
        http_client_options: Optional HTTP client configuration.
    """

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        name: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        endpoint: str | None = None,
        http_client_options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize OpenRouter adapter.

        Signature aligned with OpenAIModelAdapter for consistent usage.

        Args:
            name: Adapter name for config lookups (default "openrouter").
            model: Model name (defaults to OPENROUTER_MODEL env).
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env).
            endpoint: API base URL (defaults to OPENROUTER_BASE_URL env).
            http_client_options: Optional HTTP client config (reserved for future use).
        """
        self._name = name or "openrouter"
        self._model_name = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._base_url = endpoint or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self._http_client_options = dict(http_client_options or {})

        if not self._api_key:
            raise ValueError(
                "OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable."
            )

        if AsyncOpenAI is None:
            raise ImportError(
                "OpenAI SDK is required for OpenRouter. Install with: pip install openai"
            )

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> Literal[ComponentType.MODEL_ADAPTER]:
        return ComponentType.MODEL_ADAPTER

    def _extract_tool_calls(self, message: Any) -> list[dict[str, Any]]:
        """Extract tool calls from OpenAI message format.

        Args:
            message: OpenAI message object with tool_calls attribute.

        Returns:
            List of normalized tool calls: [{"id": str, "name": str, "arguments": dict}].
        """
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return []

        result = []
        for tc in message.tool_calls:
            try:
                arguments_dict = json.loads(tc.function.arguments)
                result.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": arguments_dict,
                })
            except (json.JSONDecodeError, AttributeError) as e:
                self._logger.warning("Failed to parse tool call: %s", e)
                continue
        return result

    def _model_input_to_messages(self, model_input: ModelInput) -> list[dict[str, Any]]:
        """Convert ModelInput messages to OpenAI API messages format."""
        messages = []
        for msg in model_input.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        return messages

    def _apply_options(
        self, api_params: dict[str, Any], options: GenerateOptions | None
    ) -> None:
        """Merge GenerateOptions into API params (in-place)."""
        if options is None:
            return
        if options.max_tokens is not None:
            api_params["max_tokens"] = options.max_tokens
        if options.temperature is not None:
            api_params["temperature"] = options.temperature
        if options.top_p is not None:
            api_params["top_p"] = options.top_p
        if options.stop is not None:
            api_params["stop"] = options.stop
        if options.metadata:
            api_params.setdefault("extra_body", {}).update(options.metadata)

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        """Generate a response using OpenRouter (IModelAdapter)."""

        messages = self._model_input_to_messages(model_input)

        api_params: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
        }

        if model_input.tools:
            api_params["tools"] = model_input.tools

        self._apply_options(api_params, options)

        response = await self._client.chat.completions.create(**api_params)

        message = response.choices[0].message
        content = message.content or ""
        tool_calls = self._extract_tool_calls(message)

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
                "model": self._model_name,
                "finish_reason": getattr(
                    response.choices[0], "finish_reason", None
                ),
            },
        )


__all__ = ["OpenRouterModelAdapter"]
