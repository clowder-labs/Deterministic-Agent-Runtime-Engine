"""Redaction utilities for telemetry payloads."""

from __future__ import annotations

from typing import Any

from dare_framework.config.types import ObservabilityConfig

_DEFAULT_REDACT_KEYS = {
    "content",
    "messages",
    "prompt",
    "tool_args",
    "tool_arguments",
    "arguments",
    "input",
    "output",
    "response",
}


def redact_payload(payload: dict[str, Any], config: ObservabilityConfig) -> dict[str, Any]:
    """Return a redacted copy of the payload based on config."""
    if not payload:
        return {}
    keys = set(config.redaction.keys) if config.redaction.keys else _DEFAULT_REDACT_KEYS
    mode = config.redaction.mode
    replacement = config.redaction.replacement

    def _redact_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: _redact_entry(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [_redact_value(item) for item in value]
        return value

    def _redact_entry(key: str, value: Any) -> Any:
        if mode == "allowlist":
            if keys and key not in keys:
                return replacement
            return _redact_value(value)
        if key in keys:
            return replacement
        return _redact_value(value)

    if not config.capture_content:
        return {k: _redact_entry(k, v) for k, v in payload.items()}

    # capture_content enabled: apply redaction rules only when keys specified
    if config.redaction.keys:
        return {k: _redact_entry(k, v) for k, v in payload.items()}

    return payload


__all__ = ["redact_payload"]
