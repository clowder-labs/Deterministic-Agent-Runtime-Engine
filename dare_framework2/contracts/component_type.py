"""Component category taxonomy used for configuration scoping."""

from __future__ import annotations

from enum import Enum


class ComponentType(Enum):
    PLANNER = "planner"
    VALIDATOR = "validator"
    REMEDIATOR = "remediator"
    MEMORY = "memory"
    MODEL_ADAPTER = "model_adapter"
    TOOL = "tool"
    SKILL = "skill"
    MCP = "mcp"
    HOOK = "hook"
    PROTOCOL_ADAPTER = "protocol_adapter"
    CONFIG_PROVIDER = "config_provider"
    PROMPT_STORE = "prompt_store"
