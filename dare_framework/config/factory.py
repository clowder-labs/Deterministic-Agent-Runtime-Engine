"""Config factory helpers."""

from __future__ import annotations

from pathlib import Path

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.file_config_provider import FileConfigProvider


def build_config_provider(
    *,
    workspace_dir: Path | str | None = None,
    user_dir: Path | str | None = None,
) -> IConfigProvider:
    """Create a default file-backed config provider."""
    return FileConfigProvider(
        workspace_dir=workspace_dir,
        user_dir=user_dir,
    )


__all__ = ["build_config_provider"]
