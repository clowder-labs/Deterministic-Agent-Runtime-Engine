"""Model domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Message:
    """A canonical chat message representation exchanged with model adapters.
    
    Attributes:
        role: The message role (system, user, assistant, tool)
        content: The message content
        name: Optional name for tool messages
        tool_call_id: Optional ID linking to a tool call
        tool_calls: Optional list of tool calls (for assistant messages)
    """
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class GenerateOptions:
    """Optional generation settings for model adapters.
    
    Attributes:
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 - 2.0)
    """
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class ModelResponse:
    """Model output including optional tool calls.
    
    Attributes:
        content: The generated text content
        tool_calls: List of tool calls requested by the model
    """
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
