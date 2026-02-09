"""Shared file tool utilities for v4.0."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from dare_framework.tool.errors import ToolError
from dare_framework.tool.types import RunContext

DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_MAX_RESULTS = 50
DEFAULT_IGNORE_DIRS = [".git", "node_modules", "__pycache__", ".venv", "venv"]


def get_tool_config(context: RunContext[Any], tool_name: str) -> dict[str, Any]:
    """Return tool-specific config dict from the run context."""
    config = getattr(context, "config", None)
    if config is None:
        deps = getattr(context, "deps", None)
        config = getattr(deps, "config", None)
    if config is None:
        return {}
    tools = None
    if hasattr(config, "tools"):
        tools = getattr(config, "tools")
    elif isinstance(config, dict):
        tools = config.get("tools")
    if isinstance(tools, dict):
        entry = tools.get(tool_name, {})
        return entry if isinstance(entry, dict) else {}
    return {}


def coerce_int(value: Any, default: int, min_value: int = 1) -> int:
    """Coerce a value to int with a lower bound and fallback."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < min_value:
        return default
    return parsed


def coerce_list(value: Any, default: Iterable[str]) -> list[str]:
    """Coerce a value to a list of strings with fallback."""
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return list(default)


def resolve_workspace_roots(context: RunContext[Any]) -> list[Path]:
    """Resolve workspace roots from config or default to project root."""
    config = getattr(context, "config", None)
    if config is None:
        deps = getattr(context, "deps", None)
        config = getattr(deps, "config", None)
    roots: list[str] | None = None
    if config is None:
        roots = None
    elif hasattr(config, "workspace_roots"):
        roots = list(getattr(config, "workspace_roots") or [])
    elif hasattr(config, "workspace_dir"):
        workspace_dir = getattr(config, "workspace_dir")
        if isinstance(workspace_dir, str) and workspace_dir.strip():
            roots = [workspace_dir]
    elif isinstance(config, dict):
        roots_value = config.get("workspace_roots")
        if isinstance(roots_value, list):
            roots = [str(item) for item in roots_value]
        elif isinstance(config.get("workspace_dir"), str):
            roots = [str(config["workspace_dir"])]
    if not roots:
        roots = [str(_default_workspace_root())]
    resolved: list[Path] = []
    for root in roots:
        resolved.append(Path(root).expanduser().resolve())
    return resolved


def _default_workspace_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return cwd


def resolve_path(path_value: Any, roots: list[Path]) -> tuple[Path, Path]:
    """Resolve a path value against workspace roots."""
    if not isinstance(path_value, str) or not path_value.strip():
        raise ToolError(code="INVALID_PATH", message="path is required", retryable=False)
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
        root = _find_root(resolved, roots)
        if root is None:
            raise ToolError(code="PATH_NOT_ALLOWED", message="path is outside workspace roots")
        return resolved, root
    root = roots[0]
    resolved = (root / candidate).resolve()
    if not _is_relative_to(resolved, root):
        raise ToolError(code="PATH_NOT_ALLOWED", message="path is outside workspace roots")
    return resolved, root


def relative_to_root(path: Path, root: Path) -> str:
    """Return a relative path string when possible."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def atomic_write(path: Path, data: bytes, mode: int | None = None) -> None:
    """Write bytes atomically to a path, preserving mode when provided."""
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent)) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if mode is not None:
            os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    except OSError as exc:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise ToolError(code="WRITE_FAILED", message=str(exc), retryable=False) from exc


def _find_root(path: Path, roots: list[Path]) -> Path | None:
    for root in roots:
        if _is_relative_to(path, root):
            return root
    return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        return path.is_relative_to(root)
    except AttributeError:
        root_str = str(root)
        path_str = str(path)
        if path_str == root_str:
            return True
        return path_str.startswith(root_str.rstrip(os.sep) + os.sep)


__all__ = [
    "DEFAULT_IGNORE_DIRS",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_RESULTS",
    "atomic_write",
    "coerce_int",
    "coerce_list",
    "get_tool_config",
    "relative_to_root",
    "resolve_path",
    "resolve_workspace_roots",
]
