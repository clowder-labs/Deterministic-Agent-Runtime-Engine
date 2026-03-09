"""Public transport serialization helpers."""

from __future__ import annotations

import dataclasses
from typing import Any


def jsonify_transport_value(value: Any) -> Any:
    """Convert typed transport payload values into JSON-safe structures."""
    if dataclasses.is_dataclass(value):
        return {str(key): jsonify_transport_value(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): jsonify_transport_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonify_transport_value(item) for item in value]
    return value


__all__ = ["jsonify_transport_value"]
