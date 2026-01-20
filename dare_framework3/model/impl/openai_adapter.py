"""OpenAI-compatible model adapter using LangChain."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from dare_framework3.model.interfaces import IModelAdapter
from dare_framework3.model.types import Message, ModelResponse, GenerateOptions

if TYPE_CHECKING:
    from dare_framework3.tool.types import ToolDefinition
    from dare_framework3.config.types import Config

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
        model: The model name (e.g., "gpt-4o", "gpt-4o-mini")
        api_key: The API key for authentication
        endpoint: Optional custom endpoint URL for self-hosted models
        http_client_options: Optional HTTP client configuration
    """

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        endpoint: str | None = None,
        http_client_options: dict[str, Any] | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._endpoint = endpoint
        self._http_client_options = dict(http_client_options or {})
        self._extra: dict[str, Any] = {}
        self._client: Any = None

    async def init(self, config: "Config | None" = None, prompts: object | None = None) -> None:
        """Initialize the adapter with configuration.
        
        Args:
            config: Framework configuration containing LLM settings
            prompts: Optional prompt templates (unused)
        """
        if config is not None:
            llm = config.llm
            if self._model is None:
                self._model = llm.model
            if self._api_key is None:
                self._api_key = llm.api_key
            if self._endpoint is None:
                self._endpoint = llm.endpoint
            if not self._http_client_options:
                llm_http_client = llm.extra.get("http_client_options") or llm.extra.get("http_client")
                if isinstance(llm_http_client, dict):
                    self._http_client_options = dict(llm_http_client)
            self._extra = {
                key: value
                for key, value in llm.extra.items()
                if key not in {"http_client_options", "http_client"}
            }
        self._client = self._build_client()

    async def generate(
        self,
        messages: list[Message],
        tools: list["ToolDefinition"] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        """Generate a response from the OpenAI-compatible model."""
        client = self._ensure_client()
        client = self._apply_options(client, options)
        if tools:
            client = client.bind_tools([self._tool_definition(tool) for tool in tools])
        self._log_client_config(client)
        response = await client.ainvoke(self._to_langchain_messages(messages))
        tool_calls = self._extract_tool_calls(response)
        return ModelResponse(content=response.content or "", tool_calls=tool_calls)

    async def generate_structured(
        self,
        messages: list[Message],
        output_schema: type[Any],
    ) -> Any:
        """Generate a structured response using function calling."""
        client = self._ensure_client()
        if hasattr(client, "with_structured_output"):
            structured = client.with_structured_output(output_schema)
            return await structured.ainvoke(self._to_langchain_messages(messages))
        try:
            return output_schema()
        except Exception:  # noqa: BLE001
            return {}

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

    def _to_langchain_messages(self, messages: list[Message]) -> list[Any]:
        """Convert framework messages to LangChain message format."""
        mapped = []
        for msg in messages:
            if msg.role == "system":
                mapped.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                mapped.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                tool_calls = self._normalize_tool_calls_for_langchain(msg.tool_calls or [])
                mapped.append(AIMessage(content=msg.content, tool_calls=tool_calls))
            elif msg.role == "tool":
                tool_call_id = msg.tool_call_id or "tool_call"
                mapped.append(ToolMessage(content=msg.content, tool_call_id=tool_call_id))
            else:
                mapped.append(HumanMessage(content=msg.content))
        return mapped

    def _apply_options(self, client: Any, options: GenerateOptions | None) -> Any:
        """Apply generation options to the client."""
        if options is None:
            return client
        bind_kwargs = {}
        if options.max_tokens is not None:
            bind_kwargs["max_tokens"] = options.max_tokens
        if options.temperature is not None:
            bind_kwargs["temperature"] = options.temperature
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

    def _tool_definition(self, tool: "ToolDefinition") -> dict[str, Any]:
        """Convert a ToolDefinition to OpenAI's function format."""
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
