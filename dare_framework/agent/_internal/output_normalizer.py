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


def normalize_run_output(output: Any) -> str | None:
    """Normalize RunResult.output for display/logging channels."""
    if output is None:
        return None
    text = extract_text_payload(output)
    if text:
        return text
    if isinstance(output, dict):
        for key in ("content", "text", "output", "message", "result"):
            if key not in output:
                continue
            value = output.get(key)
            if value is None:
                return None
            if isinstance(value, str) and not value.strip():
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
    content = normalize_run_output(output) or ""
    envelope_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    envelope_usage = usage if isinstance(usage, dict) else None
    return {
        "content": content,
        "metadata": envelope_metadata,
        "usage": envelope_usage,
    }


__all__ = ["build_output_envelope", "extract_text_payload", "normalize_run_output"]
