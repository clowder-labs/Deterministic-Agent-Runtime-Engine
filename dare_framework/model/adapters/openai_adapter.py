"""OpenAI-compatible model adapter using LangChain."""

from __future__ import annotations

import json
import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Literal

from dare_framework.tool.types import CapabilityDescriptor
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse, GenerateOptions
from dare_framework.infra.component import ComponentType

if TYPE_CHECKING:
    from dare_framework.tool.types import ToolDefinition

# Optional LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
except ImportError:  # pragma: no cover - handled at runtime
    ChatOpenAI = None  # type: ignore[assignment]
    AIMessage = None  # type: ignore[assignment]
    HumanMessage = None  # type: ignore[assignment]
    SystemMessage = None  # type: ignore[assignment]
    ToolMessage = None  # type: ignore[assignment]


class OpenAIModelAdapter(IModelAdapter):
    """Model adapter for OpenAI-compatible APIs using LangChain.

    Supports OpenAI, Azure OpenAI, and any OpenAI-compatible endpoint.
    Requires the `langchain-openai` package to be installed.

    Args:
        model: The model name (e.g., "gpt-4o", "gpt-4o-mini", "qwen-plus")
        api_key: The API key for authentication
        endpoint: Optional custom endpoint URL for self-hosted models
        http_client_options: Optional HTTP client configuration
    """


    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        name: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        endpoint: str | None = None,
        http_client_options: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._name = name or "openai"
        self._model = model
        self._api_key = api_key
        self._endpoint = endpoint
        self._http_client_options = dict(http_client_options or {})
        self._extra: dict[str, Any] = dict(extra or {})
        self._client: Any = None



    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model or "gpt-4o-mini"

    @property
    def component_type(self) -> Literal[ComponentType.MODEL_ADAPTER]:
        return ComponentType.MODEL_ADAPTER

    async def generate(
        self,
        model_input: ModelInput,
        *,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        """Generate a response from the OpenAI-compatible model."""
        client = self._ensure_client()
        client = self._apply_options(client, options)
        
        # Build tools directly from CapabilityDescriptor objects
        if model_input.tools:
            openai_tools = []
            for tool in model_input.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                })
            client = client.bind_tools(openai_tools)
        
        self._log_client_config(client)
        response = await client.ainvoke(self._to_langchain_messages(model_input.messages))
        
        tool_calls = self._extract_tool_calls(response)
        usage = self._extract_usage(response)
        thinking_content = self._extract_thinking_content(response)
        
        return ModelResponse(
            content=response.content or "",
            tool_calls=tool_calls,
            usage=usage,
            thinking_content=thinking_content,
        )

    def _ensure_client(self) -> Any:
        """Ensure the LangChain client is initialized."""
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> Any:
        """Build the LangChain ChatOpenAI client."""
        if ChatOpenAI is None:
            raise RuntimeError("langchain-openai is required for OpenAIModelAdapter")

        model = self._model or "gpt-4o-mini"
        kwargs: dict[str, Any] = {"model": model}

        if self._api_key:
            kwargs["api_key"] = self._api_key
        elif self._endpoint:
            # Local/self-hosted endpoints still require a key; use placeholder
            kwargs["api_key"] = "dummy-key"

        if self._endpoint:
            kwargs["base_url"] = self._endpoint

        kwargs.update(self._extra)

        sync_client, async_client = self._build_http_clients()
        if sync_client is not None:
            kwargs["http_client"] = sync_client
        if async_client is not None:
            kwargs["http_async_client"] = async_client

        return ChatOpenAI(**kwargs)

    def _to_langchain_messages(self, messages: list[Any]) -> list[Any]:
        """Convert framework messages to LangChain message format."""
        mapped = []
        for msg in messages:
            role = str(getattr(msg, "role", "user"))
            content = self._serialize_langchain_content(msg)
            if role == "system":
                mapped.append(SystemMessage(content=content))
            elif role == "user":
                mapped.append(HumanMessage(content=content))
            elif role == "assistant":
                tool_calls = self._extract_message_tool_calls(msg)
                tool_calls = self._normalize_tool_calls_for_langchain(tool_calls)
                mapped.append(AIMessage(content=content, tool_calls=tool_calls))
            elif role == "tool":
                tool_call_id = self._extract_message_tool_call_id(msg) or "tool_call"
                mapped.append(ToolMessage(content=content, tool_call_id=tool_call_id))
            else:
                mapped.append(HumanMessage(content=content))
        return mapped

    def _serialize_langchain_content(self, message: Any) -> Any:
        text = self._message_text(message)
        attachments = list(getattr(message, "attachments", []) or [])
        if not attachments:
            return text

        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        for attachment in attachments:
            if str(getattr(attachment, "kind", "")).strip().lower() != "image":
                raise ValueError("unsupported attachment kind for OpenAI serialization")
            content.append({"type": "image_url", "image_url": {"url": attachment.uri}})
        return content

    def _message_text(self, message: Any) -> str:
        text = getattr(message, "text", None)
        if isinstance(text, str):
            return text
        return ""

    def _extract_message_tool_calls(self, message: Any) -> Any:
        data = getattr(message, "data", None)
        if isinstance(data, dict) and isinstance(data.get("tool_calls"), list):
            return data["tool_calls"]
        return []

    def _extract_message_tool_call_id(self, message: Any) -> str | None:
        data = getattr(message, "data", None)
        if isinstance(data, dict):
            tool_call_id = data.get("tool_call_id")
            if isinstance(tool_call_id, str) and tool_call_id.strip():
                return tool_call_id
        name = getattr(message, "name", None)
        if isinstance(name, str) and name.strip():
            return name
        return None

    def _apply_options(self, client: Any, options: GenerateOptions | None) -> Any:
        """Apply generation options to the client."""
        if options is None:
            return client
        bind_kwargs = {}
        if options.max_tokens is not None:
            bind_kwargs["max_tokens"] = options.max_tokens
        if options.temperature is not None:
            bind_kwargs["temperature"] = options.temperature
        if options.top_p is not None:
            bind_kwargs["top_p"] = options.top_p
        if options.stop is not None:
            bind_kwargs["stop"] = options.stop
        if not bind_kwargs:
            return client
        return client.bind(**bind_kwargs)

    def _extract_tool_calls(self, response: Any) -> list[dict[str, Any]]:
        """Extract and normalize tool calls from the response."""
        raw_calls = getattr(response, "tool_calls", None)
        if not raw_calls:
            raw_calls = getattr(response, "additional_kwargs", {}).get("tool_calls", [])

        normalized = []
        for call in raw_calls or []:
            name, args, call_id = self._extract_tool_call_fields(call)
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            if args is None:
                args = {}
            normalized.append({"id": call_id, "name": name, "arguments": args})
        return normalized

    def _extract_tool_call_fields(self, call: Any) -> tuple[str | None, Any, str | None]:
        """Extract name, arguments, and ID from a tool call."""
        if isinstance(call, dict):
            name = call.get("name") or call.get("function", {}).get("name")
            args = call.get("args") or call.get("arguments") or call.get("function", {}).get("arguments")
            call_id = call.get("id") or call.get("tool_call_id")
        else:
            name = getattr(call, "name", None)
            args = getattr(call, "args", None) or getattr(call, "arguments", None)
            call_id = getattr(call, "id", None)
        return name, args, call_id

    def _normalize_tool_calls_for_langchain(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalize tool calls for LangChain's expected format."""
        normalized = []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            normalized.append({
                "id": call.get("id"),
                "name": call.get("name"),
                "args": call.get("arguments") if "arguments" in call else call.get("args", {}),
            })
        return normalized

    def _extract_usage(self, response: Any) -> dict[str, Any] | None:
        """Extract usage information from the response."""
        usage = getattr(response, "response_metadata", {}).get("token_usage")
        if usage:
            normalized = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
            reasoning_tokens = self._extract_reasoning_tokens(usage)
            if reasoning_tokens is not None:
                normalized["reasoning_tokens"] = reasoning_tokens
            return normalized
        return None

    def _extract_reasoning_tokens(self, usage: dict[str, Any]) -> int | None:
        """Extract reasoning token count from provider-specific usage payloads."""
        candidates: list[Any] = [
            usage.get("reasoning_tokens"),
            usage.get("output_tokens_details", {}).get("reasoning_tokens")
            if isinstance(usage.get("output_tokens_details"), dict)
            else None,
            usage.get("output_tokens_details", {}).get("reasoning")
            if isinstance(usage.get("output_tokens_details"), dict)
            else None,
            usage.get("completion_tokens_details", {}).get("reasoning_tokens")
            if isinstance(usage.get("completion_tokens_details"), dict)
            else None,
        ]
        for candidate in candidates:
            try:
                if candidate is None:
                    continue
                return int(candidate)
            except (TypeError, ValueError):
                continue
        return None

    def _extract_thinking_content(self, response: Any) -> str | None:
        """Extract provider reasoning text into framework-level thinking content."""
        additional_kwargs = getattr(response, "additional_kwargs", {})
        if isinstance(additional_kwargs, dict):
            for key in ("reasoning_content", "reasoning", "thinking"):
                content = _coerce_text(additional_kwargs.get(key))
                if content:
                    return content

        response_metadata = getattr(response, "response_metadata", {})
        if isinstance(response_metadata, dict):
            for key in ("reasoning_content", "reasoning", "thinking"):
                content = _coerce_text(response_metadata.get(key))
                if content:
                    return content
        return None

    def _log_client_config(self, client: Any) -> None:
        """Log client configuration for debugging."""
        if not self._logger.isEnabledFor(logging.DEBUG):
            return
        base_url = (
            getattr(getattr(client, "client", None), "base_url", None)
            or getattr(client, "base_url", None)
            or getattr(getattr(client, "_client", None), "base_url", None)
        )
        model_name = getattr(client, "model_name", None) or getattr(client, "model", None)
        self._logger.debug(
            "OpenAIModelAdapter generate call",
            extra={
                "model": model_name or self._model,
                "base_url": str(base_url) if base_url else None,
                "has_api_key": bool(self._api_key),
                "extra": bool(self._extra),
            },
        )

    def _build_http_clients(self) -> tuple[Any | None, Any | None]:
        """Build custom HTTP clients if options are provided."""
        if not self._http_client_options:
            return None, None
        try:
            import httpx
        except Exception:
            return None, None
        try:
            opts = dict(self._http_client_options)
            sync_client = httpx.Client(**opts)
            async_client = httpx.AsyncClient(**opts)
            return sync_client, async_client
        except Exception:
            return None, None



__all__ = ["OpenAIModelAdapter"]


def _coerce_text(value: Any) -> str | None:
    """Coerce heterogenous provider reasoning payloads into a non-empty string."""
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
