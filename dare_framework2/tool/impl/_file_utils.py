from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_MAX_RESULTS = 50
DEFAULT_IGNORE_DIRS = [".git", "node_modules", "__pycache__", ".venv", "venv"]


def get_tool_config(context: Any, tool_name: str) -> dict[str, Any]:
    """Best-effort lookup for per-tool config.

    `dare_framework2.tool.types.RunContext.config` is intentionally typed as `Any`.
    Tools should tolerate missing/unknown config objects and fall back to safe defaults.
    """
    config = getattr(context, "config", None)
    if config is None:
        return {}
    tools = getattr(config, "tools", None)
    if not isinstance(tools, dict):
        return {}
    section = tools.get(tool_name, {})
    return section if isinstance(section, dict) else {}


def coerce_int(value: Any, default: int, *, min_value: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < min_value:
        return default
    return parsed


def coerce_list(value: Any, default: Iterable[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return list(default)


def resolve_workspace_roots(context: Any) -> list[Path]:
    """Resolve workspace roots from config or default to CWD.

    Returning absolute, resolved roots makes subsequent path checks robust against
    symlink escapes and `..` traversal.
    """
    config = getattr(context, "config", None)
    roots = getattr(config, "workspace_roots", None) if config is not None else None
    if not isinstance(roots, list) or not roots:
        roots = [str(Path.cwd())]
    resolved: list[Path] = []
    for root in roots:
        resolved.append(Path(str(root)).expanduser().resolve())
    return resolved


def resolve_path(path_value: Any, roots: list[Path]) -> tuple[Path, Path]:
    """Resolve a user-provided path against workspace roots.

    - Absolute paths must fall under one of the roots.
    - Relative paths are interpreted relative to the first root.
    """
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("INVALID_PATH")

    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
        root = _find_root(resolved, roots)
        if root is None:
            raise PermissionError("PATH_NOT_ALLOWED")
        return resolved, root

    root = roots[0]
    resolved = (root / candidate).resolve()
    if not _is_relative_to(resolved, root):
        raise PermissionError("PATH_NOT_ALLOWED")
    return resolved, root


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        # Should not happen for validated paths; keep a safe fallback for robustness.
        return str(path)


def atomic_write(path: Path, data: bytes, *, mode: int | None = None) -> None:
    """Atomically write bytes to `path` using temp file + rename."""
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
        raise OSError("WRITE_FAILED") from exc


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

