"""MCP configuration loader.

The MCPConfigLoader scans directories for MCP configuration files and
parses them into MCPServerConfig objects. It supports JSON, YAML, and
Markdown files (extracting JSON/YAML from code blocks).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dare_framework.mcp.types import MCPConfigFile, MCPServerConfig

logger = logging.getLogger(__name__)


class MCPConfigLoader:
    """Scans directories and loads MCP server configurations.

    Supports multiple configuration file formats:
    - JSON (.json)
    - YAML (.yaml, .yml) - requires pyyaml
    - Markdown (.md) - extracts JSON/YAML from code blocks

    Each file can define one or multiple MCP servers.

    Example directory structure:
        .dare/mcp/
        ├── filesystem.json      # Single server
        ├── dev_tools.json       # Multiple servers
        └── team_services.yaml   # YAML format

    Example usage:
        loader = MCPConfigLoader([".dare/mcp", "~/.dare/mcp"])
        configs = loader.load()
        for config in configs:
            print(f"Found MCP server: {config.name}")
    """

    # Supported file extensions
    JSON_EXTENSIONS = {".json"}
    YAML_EXTENSIONS = {".yaml", ".yml"}
    MARKDOWN_EXTENSIONS = {".md", ".markdown"}

    def __init__(
        self,
        paths: list[str | Path],
        *,
        recursive: bool = False,
    ) -> None:
        """Initialize the loader.

        Args:
            paths: List of directories to scan for MCP configuration files.
                   Paths can include ~ for home directory expansion.
            recursive: Whether to scan subdirectories recursively.
        """
        self._paths = [Path(p).expanduser() for p in paths]
        self._recursive = recursive

    def load(self) -> list[MCPServerConfig]:
        """Scan directories and load all MCP server configurations.

        Returns:
            List of MCPServerConfig objects from all discovered files.
            Invalid configurations are logged as warnings and skipped.
        """
        all_configs: list[MCPServerConfig] = []

        for base_path in self._paths:
            if not base_path.exists():
                logger.debug(f"MCP config path does not exist: {base_path}")
                continue

            if not base_path.is_dir():
                # Single file
                configs = self._load_file(base_path)
                all_configs.extend(configs)
            else:
                # Directory - scan for config files
                files = self._scan_directory(base_path)
                for file_path in files:
                    configs = self._load_file(file_path)
                    all_configs.extend(configs)

        # Log summary
        if all_configs:
            logger.info(f"Loaded {len(all_configs)} MCP server configurations")
        else:
            logger.debug("No MCP server configurations found")

        return all_configs

    def _scan_directory(self, directory: Path) -> list[Path]:
        """Scan a directory for configuration files.

        Args:
            directory: Directory to scan.

        Returns:
            List of configuration file paths.
        """
        files: list[Path] = []
        supported_extensions = (
            self.JSON_EXTENSIONS | self.YAML_EXTENSIONS | self.MARKDOWN_EXTENSIONS
        )

        try:
            if self._recursive:
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        file_path = Path(root) / filename
                        if file_path.suffix.lower() in supported_extensions:
                            files.append(file_path)
            else:
                for item in directory.iterdir():
                    if item.is_file() and item.suffix.lower() in supported_extensions:
                        files.append(item)

        except PermissionError:
            logger.warning(f"Permission denied: {directory}")

        return sorted(files)

    def _load_file(self, file_path: Path) -> list[MCPServerConfig]:
        """Load MCP configurations from a single file.

        Args:
            file_path: Path to the configuration file.

        Returns:
            List of MCPServerConfig objects (may be empty on error).
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix in self.JSON_EXTENSIONS:
                data = self._parse_json(file_path)
            elif suffix in self.YAML_EXTENSIONS:
                data = self._parse_yaml(file_path)
            elif suffix in self.MARKDOWN_EXTENSIONS:
                data = self._parse_markdown(file_path)
            else:
                logger.debug(f"Unsupported file type: {file_path}")
                return []

            if data is None:
                return []

            # Parse into MCPConfigFile
            config_file = MCPConfigFile.from_dict(data, source_path=str(file_path))

            # Validate each server config
            valid_configs: list[MCPServerConfig] = []
            for server in config_file.servers:
                errors = server.validate()
                if errors:
                    logger.warning(
                        f"Invalid MCP config in {file_path}: {server.name}: {errors}"
                    )
                else:
                    valid_configs.append(server)
                    logger.debug(f"Loaded MCP config: {server.name} from {file_path}")

            return valid_configs

        except Exception as e:
            logger.warning(f"Failed to load MCP config from {file_path}: {e}")
            return []

    def _parse_json(self, file_path: Path) -> dict[str, Any] | None:
        """Parse a JSON configuration file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_yaml(self, file_path: Path) -> dict[str, Any] | None:
        """Parse a YAML configuration file."""
        try:
            import yaml
        except ImportError:
            logger.warning(
                f"pyyaml not installed, skipping YAML file: {file_path}"
            )
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _parse_markdown(self, file_path: Path) -> dict[str, Any] | None:
        """Parse MCP configuration from Markdown code blocks.

        Extracts JSON or YAML from the first code block that contains
        valid MCP configuration (has 'name' or 'servers' key).

        Example Markdown:
            # MCP Servers

            ```json
            {
              "servers": [
                {"name": "fs", "transport": "stdio", "command": ["mcp-fs"]}
              ]
            }
            ```
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Match code blocks: ```json ... ``` or ```yaml ... ```
        code_block_pattern = r"```(?:json|yaml|yml)?\s*\n(.*?)```"
        matches = re.findall(code_block_pattern, content, re.DOTALL)

        for block in matches:
            block = block.strip()
            if not block:
                continue

            # Try JSON first
            try:
                data = json.loads(block)
                if self._is_mcp_config(data):
                    return data
            except json.JSONDecodeError:
                pass

            # Try YAML
            try:
                import yaml

                data = yaml.safe_load(block)
                if self._is_mcp_config(data):
                    return data
            except ImportError:
                pass
            except Exception:
                pass

        return None

    def _is_mcp_config(self, data: Any) -> bool:
        """Check if data looks like MCP configuration."""
        if not isinstance(data, dict):
            return False
        return "name" in data or "servers" in data


def load_mcp_configs(
    paths: list[str | Path] | None = None,
    *,
    workspace_dir: str | Path | None = None,
    user_dir: str | Path | None = None,
) -> list[MCPServerConfig]:
    """Convenience function to load MCP configurations.

    If paths is not provided, uses default locations:
    - {workspace_dir}/.dare/mcp
    - {user_dir}/.dare/mcp

    Args:
        paths: Explicit list of paths to scan.
        workspace_dir: Workspace directory for default path.
        user_dir: User directory for default path.

    Returns:
        List of MCPServerConfig objects.
    """
    if paths is None:
        paths = []
        if workspace_dir:
            paths.append(Path(workspace_dir) / ".dare" / "mcp")
        if user_dir:
            paths.append(Path(user_dir) / ".dare" / "mcp")
        if not paths:
            # Fallback to current directory
            paths.append(Path.cwd() / ".dare" / "mcp")

    loader = MCPConfigLoader(paths)
    return loader.load()


__all__ = ["MCPConfigLoader", "load_mcp_configs"]
