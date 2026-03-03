"""Model domain data types and prompt/result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework.context.types import Message
from dare_framework.tool.types import CapabilityDescriptor


@dataclass(frozen=True)
class Prompt:
    """Prompt definition loaded from manifests or built-in defaults."""

    prompt_id: str
    role: str
    content: str
    supported_models: list[str]
    order: int
    version: str | None = None
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Prompt:
        """Create a Prompt from a manifest dictionary."""
        prompt_id = str(data.get("prompt_id", ""))
        role = str(data.get("role", ""))
        content = str(data.get("content", ""))
        supported_models_raw = data.get("supported_models", [])
        if not isinstance(supported_models_raw, list):
            supported_models = []
        else:
            supported_models = [str(item) for item in supported_models_raw]
        order_raw = data.get("order", 0)
        try:
            order = int(order_raw)
        except (TypeError, ValueError):
            order = 0
        version = data.get("version")
        name = data.get("name")
        metadata_raw = data.get("metadata")
        metadata = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
        return cls(
            prompt_id=prompt_id,
            role=role,
            content=content,
            supported_models=supported_models,
            order=order,
            version=str(version) if version is not None else None,
            name=str(name) if name is not None else None,
            metadata=metadata,
        )


@dataclass(frozen=True)
class ModelInput:
    """Model input representation for model adapters."""

    messages: list[Message]
    tools: list[CapabilityDescriptor] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """Model response including optional tool calls."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    thinking_content: str | None = None


@dataclass(frozen=True)
class GenerateOptions:
    """Generation options for model adapters."""

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["Prompt", "ModelInput", "ModelResponse", "GenerateOptions"]
