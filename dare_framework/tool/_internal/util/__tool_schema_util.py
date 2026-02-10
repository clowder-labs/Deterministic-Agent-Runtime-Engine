"""Schema inference helpers for tool execute signatures."""

from __future__ import annotations

import dataclasses
import inspect
import re
import types
import typing
from enum import Enum
from typing import Any, Callable, get_args, get_origin, get_type_hints

from dare_framework.tool.types import ToolResult


_NONE_TYPE = type(None)


def infer_input_schema_from_execute(execute: Callable[..., Any]) -> dict[str, Any]:
    """Infer JSON schema for tool input from execute signature and docstring."""
    signature = inspect.signature(execute)
    hints = _safe_type_hints(execute)
    param_docs, _ = _parse_docstring(inspect.getdoc(execute) or "")

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, parameter in signature.parameters.items():
        if name in {"self", "run_context"}:
            continue
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue

        annotation = hints.get(name, Any)
        field_schema = _annotation_to_schema(annotation)
        description = param_docs.get(name)
        if description:
            field_schema["description"] = description

        if parameter.default is inspect.Signature.empty:
            required.append(name)
        else:
            default = parameter.default
            if _is_json_scalar(default):
                field_schema["default"] = default

        properties[name] = field_schema

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def infer_output_schema_from_execute(execute: Callable[..., Any]) -> dict[str, Any] | None:
    """Infer JSON schema for tool output from execute return annotation."""
    hints = _safe_type_hints(execute)
    return_annotation = hints.get("return", inspect.Signature.empty)
    output_annotation = _extract_tool_result_output_annotation(return_annotation)
    if output_annotation is None:
        return None

    schema = _annotation_to_schema(output_annotation)
    _, return_doc = _parse_docstring(inspect.getdoc(execute) or "")
    if return_doc:
        schema["description"] = return_doc
    return schema


def _safe_type_hints(target: Callable[..., Any]) -> dict[str, Any]:
    try:
        return get_type_hints(target)
    except Exception:
        return {}


def _extract_tool_result_output_annotation(annotation: Any) -> Any | None:
    if annotation in {inspect.Signature.empty, Any}:
        return dict[str, Any]
    origin = get_origin(annotation)
    if origin is ToolResult:
        args = get_args(annotation)
        return args[0] if args else dict[str, Any]
    if annotation is ToolResult:
        return dict[str, Any]
    return None


def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
    if annotation in {inspect.Signature.empty, Any, object}:
        return {"type": "object"}

    origin = get_origin(annotation)

    if origin is not None:
        if origin is list:
            args = get_args(annotation)
            item_type = args[0] if args else Any
            return {"type": "array", "items": _annotation_to_schema(item_type)}
        if origin is dict:
            args = get_args(annotation)
            value_type = args[1] if len(args) > 1 else Any
            return {"type": "object", "additionalProperties": _annotation_to_schema(value_type)}
        if origin in {types.UnionType, typing.Union}:
            args = [arg for arg in get_args(annotation) if arg is not _NONE_TYPE]
            includes_none = len(args) != len(get_args(annotation))
            if len(args) == 1:
                schema = _annotation_to_schema(args[0])
                if includes_none:
                    return {"anyOf": [schema, {"type": "null"}]}
                return schema
            return {"anyOf": [_annotation_to_schema(arg) for arg in get_args(annotation)]}
        literal_type = getattr(typing, "Literal", None)
        if literal_type is not None and origin is literal_type:
            values = list(get_args(annotation))
            enum_schema: dict[str, Any] = {"enum": values}
            first = next((value for value in values if value is not None), None)
            if isinstance(first, bool):
                enum_schema["type"] = "boolean"
            elif isinstance(first, int):
                enum_schema["type"] = "integer"
            elif isinstance(first, float):
                enum_schema["type"] = "number"
            elif isinstance(first, str):
                enum_schema["type"] = "string"
            return enum_schema
        annotated_type = getattr(typing, "Annotated", None)
        if annotated_type is not None and origin is annotated_type:
            args = get_args(annotation)
            return _annotation_to_schema(args[0]) if args else {"type": "object"}

    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation in {dict, list}:
        return {"type": "object"} if annotation is dict else {"type": "array"}

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        values = [member.value for member in annotation]
        schema: dict[str, Any] = {"enum": values}
        if values:
            if isinstance(values[0], bool):
                schema["type"] = "boolean"
            elif isinstance(values[0], int):
                schema["type"] = "integer"
            elif isinstance(values[0], float):
                schema["type"] = "number"
            else:
                schema["type"] = "string"
        return schema

    if _is_typed_dict_class(annotation):
        hints = _safe_type_hints(annotation)
        properties: dict[str, Any] = {}
        for key, value in hints.items():
            properties[key] = _annotation_to_schema(value)
        required = sorted(getattr(annotation, "__required_keys__", set()) or set())
        schema = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    if dataclasses.is_dataclass(annotation):
        properties: dict[str, Any] = {}
        required: list[str] = []
        for field in dataclasses.fields(annotation):
            properties[field.name] = _annotation_to_schema(field.type)
            if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
                required.append(field.name)
        schema = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    model_json_schema = getattr(annotation, "model_json_schema", None)
    if callable(model_json_schema):
        try:
            schema = model_json_schema()
            if isinstance(schema, dict):
                return schema
        except Exception:
            pass

    return {"type": "object"}


def _is_typed_dict_class(annotation: Any) -> bool:
    return (
        isinstance(annotation, type)
        and hasattr(annotation, "__annotations__")
        and hasattr(annotation, "__total__")
        and isinstance(getattr(annotation, "__annotations__", None), dict)
    )


def _is_json_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _parse_docstring(doc: str) -> tuple[dict[str, str], str | None]:
    param_docs: dict[str, str] = {}
    return_doc: str | None = None
    if not doc:
        return param_docs, return_doc

    for name, description in re.findall(r":param\s+(\w+)\s*:\s*(.+)", doc):
        param_docs[name] = description.strip()
    returns_match = re.search(r":returns?:\s*(.+)", doc)
    if returns_match:
        return_doc = returns_match.group(1).strip()

    state: str | None = None
    current_param: str | None = None
    for raw_line in doc.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered in {"args:", "arguments:", "parameters:"}:
            state = "args"
            current_param = None
            continue
        if lowered in {"returns:", "return:"}:
            state = "returns"
            current_param = None
            continue
        if not stripped:
            current_param = None
            continue

        if state == "args":
            match = re.match(r"^(\w+)\s*(?:\([^)]+\))?:\s*(.+)$", stripped)
            if match:
                current_param = match.group(1)
                param_docs[current_param] = match.group(2).strip()
                continue
            if current_param and line.startswith((" ", "\t")):
                param_docs[current_param] = f"{param_docs[current_param]} {stripped}".strip()

        if state == "returns":
            if return_doc is None:
                return_doc = stripped
            elif line.startswith((" ", "\t")):
                return_doc = f"{return_doc} {stripped}".strip()

    return param_docs, return_doc


__all__ = [
    "infer_input_schema_from_execute",
    "infer_output_schema_from_execute",
]
