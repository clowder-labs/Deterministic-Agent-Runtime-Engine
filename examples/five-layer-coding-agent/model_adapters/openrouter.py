"""OpenRouter model adapter using OpenAI SDK."""
from __future__ import annotations

import json
import os
from typing import Any

from dare_framework.model import Prompt, ModelResponse


class OpenRouterModelAdapter:
    """Model adapter for OpenRouter API (compatible with OpenAI SDK)."""

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        """Initialize OpenRouter adapter.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
            model: Model name (defaults to OPENROUTER_MODEL env var).
            base_url: API base URL (defaults to OPENROUTER_BASE_URL env var).
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")

        # Lazy import to avoid dependency if not using OpenRouter mode
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI SDK is required for OpenRouter. Install with: pip install openai"
            ) from e

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _extract_tool_calls(self, message: Any) -> list[dict[str, Any]]:
        """Extract tool calls from OpenAI message format.

        Args:
            message: OpenAI message object with tool_calls attribute

        Returns:
            List of normalized tool calls: [{"id": str, "name": str, "arguments": dict}]
        """
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return []

        result = []
        for tc in message.tool_calls:
            try:
                # OpenAI format: {id, type, function: {name, arguments(JSON string)}}
                # Parse JSON string to dict
                arguments_dict = json.loads(tc.function.arguments)

                result.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": arguments_dict
                })
            except (json.JSONDecodeError, AttributeError) as e:
                # Skip invalid tool calls - don't crash
                print(f"[WARN] Failed to parse tool call: {e}")
                continue

        return result

    async def generate(self, prompt: Prompt, **kwargs: Any) -> ModelResponse:
        """Generate a response using OpenRouter.

        Args:
            prompt: The prompt to generate from.
            **kwargs: Additional generation options.

        Returns:
            ModelResponse with generated content.
        """
        # Convert Prompt to OpenAI messages format
        messages = []
        for msg in prompt.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Prepare API call parameters
        api_params = {
            "model": self.model_name,
            "messages": messages,
        }

        # Add tools if available (for function calling)
        if prompt.tools:
            api_params["tools"] = prompt.tools

        # Merge with additional kwargs
        api_params.update(kwargs)

        # Call OpenRouter API
        response = await self.client.chat.completions.create(**api_params)

        # Extract message content and tool calls
        message = response.choices[0].message
        content = message.content or ""

        # Extract tool_calls from the message
        tool_calls = self._extract_tool_calls(message)

        # Debug: log tool calls extraction
        if hasattr(message, "tool_calls") and message.tool_calls:
            print(f"[DEBUG] Model returned {len(message.tool_calls)} tool calls")
            for tc in message.tool_calls:
                print(f"  - {tc.function.name}")
        else:
            print(f"[DEBUG] Model returned NO tool calls (finish_reason: {response.choices[0].finish_reason})")
            if prompt.tools:
                print(f"[DEBUG] Tools were provided to model: {len(prompt.tools)} tools")
                print(f"[DEBUG] Model may not support function calling")

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            metadata={
                "model": self.model_name,
                "finish_reason": response.choices[0].finish_reason,
            }
        )
