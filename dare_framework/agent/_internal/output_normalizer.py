"""Normalize heterogeneous agent outputs into displayable text."""

from __future__ import annotations

import ast
import json
from typing import Any


def _try_parse_serialized_container(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    if not (
        (stripped.startswith("[") and stripped.endswith("]"))
        or (stripped.startswith("{") and stripped.endswith("}"))
    ):
        return None

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(stripped)
        except Exception:
            continue
        if isinstance(parsed, (list, dict)):
            return parsed
    return None


def extract_text_payload(value: Any) -> str | None:
    """Extract textual payload from nested model/tool output structures."""
    if value is None:
        return None

    if isinstance(value, str):
        if not value.strip():
            return None
        parsed = _try_parse_serialized_container(value)
        if parsed is not None:
            parsed_text = extract_text_payload(parsed)
            if parsed_text:
                return parsed_text
        return value

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            part = extract_text_payload(item)
            if part:
                parts.append(part)
        if not parts:
            return None
        merged = "".join(parts)
        return merged if merged.strip() else None

    if isinstance(value, dict):
        for key in ("content", "text", "output", "message", "result"):
            if key in value:
                extracted = extract_text_payload(value.get(key))
                if extracted:
                    return extracted
        return None

    normalized = str(value).strip()
    return normalized or None


def _has_meaningful_fallback_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _extract_raw_text_field(output: Any) -> str | None:
    if not isinstance(output, dict):
        return None
    for key in ("content", "text", "output", "message", "result"):
        value = output.get(key)
        if isinstance(value, str):
            return value
    return None


def normalize_run_output(output: Any) -> str | None:
    """Normalize RunResult.output for display/logging channels."""
    if output is None:
        return None
    text = extract_text_payload(output)
    if text:
        return text
    if isinstance(output, dict):
        text_keys = ("content", "text", "output", "message", "result")
        present_text_keys = [key for key in text_keys if key in output]
        if present_text_keys:
            has_non_text_fallback = any(
                _has_meaningful_fallback_value(value)
                for key, value in output.items()
                if key not in text_keys
            )
            if not has_non_text_fallback:
                all_text_fields_empty = all(
                    extract_text_payload(output.get(key)) is None
                    for key in present_text_keys
                )
                if all_text_fields_empty:
                    return None
        try:
            return json.dumps(output, ensure_ascii=False, indent=2)
        except TypeError:
            pass
    normalized = str(output).strip()
    return normalized or None


def build_output_envelope(
    output: Any,
    *,
    metadata: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized RunResult.output envelope.

    Envelope schema:
    - content: str
    - metadata: dict
    - usage: dict | None
    """
    if isinstance(output, str):
        content = normalize_run_output(output) or ""
    elif isinstance(output, dict):
        raw_text = _extract_raw_text_field(output)
        text_keys = {"content", "text", "output", "message", "result"}
        has_non_text_fallback = any(
            _has_meaningful_fallback_value(value)
            for key, value in output.items()
            if key not in text_keys
        )
        if isinstance(raw_text, str) and raw_text.strip() and has_non_text_fallback:
            content = raw_text
        else:
            content = normalize_run_output(output) or ""
    else:
        content = normalize_run_output(output) or ""
    envelope_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    envelope_usage = dict(usage) if isinstance(usage, dict) and usage else None
    return {
        "content": content,
        "metadata": envelope_metadata,
        "usage": envelope_usage,
    }


__all__ = ["build_output_envelope", "extract_text_payload", "normalize_run_output"]
