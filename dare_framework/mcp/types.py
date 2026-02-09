"""MCP configuration types and data models.

This module defines the data structures for MCP server configuration,
supporting multiple transport types (stdio, http, grpc).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TransportType(str, Enum):
    """Supported MCP transport types."""

    STDIO = "stdio"
    HTTP = "http"
    GRPC = "grpc"


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for a single MCP server.

    Attributes:
        name: Unique identifier for this MCP server.
        transport: Transport type (stdio, http, grpc).
        command: Command to launch the server (stdio only).
        env: Environment variables for the subprocess (stdio only).
        url: HTTP endpoint URL (http only).
        headers: HTTP headers for authentication (http only).
        endpoint: gRPC endpoint address (grpc only).
        tls: Whether to use TLS for gRPC (grpc only).
        timeout_seconds: Connection/request timeout in seconds.
        enabled: Whether this server is enabled.
    """

    name: str
    transport: TransportType = TransportType.STDIO

    # stdio transport options
    command: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    # http transport options
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    # grpc transport options
    endpoint: str = ""
    tls: bool = False

    # common options
    timeout_seconds: int = 30
    enabled: bool = True
    cwd: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source_path: str = "") -> MCPServerConfig:
        """Create MCPServerConfig from a dictionary.

        Args:
            data: Dictionary containing server configuration.

        Returns:
            MCPServerConfig instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        name = data.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("MCP server config requires a 'name' field")

        transport_str = data.get("transport", "stdio")
        try:
            transport = TransportType(transport_str)
        except ValueError:
            raise ValueError(
                f"Invalid transport type: {transport_str}. "
                f"Must be one of: {[t.value for t in TransportType]}"
            )

        # Parse transport-specific options
        command = data.get("command", [])
        if isinstance(command, str):
            command = [command]
        command = list(command) if command else []

        env = dict(data.get("env", {}))
        url = str(data.get("url", ""))
        headers = dict(data.get("headers", {}))
        endpoint = str(data.get("endpoint", ""))
        tls = bool(data.get("tls", False))
        timeout_seconds = int(data.get("timeout_seconds", 30))
        enabled = bool(data.get("enabled", True))
        cwd = data.get("cwd")
        cwd = str(cwd) if cwd else None
        if not cwd and source_path and transport == TransportType.STDIO:
            # 默认：stdio 时 cwd 为含 .dare 的目录（配置文件在 .dare/mcp/xxx.json）
            from pathlib import Path
            p = Path(source_path).resolve()
            if len(p.parents) >= 3:
                cwd = str(p.parent.parent.parent)

        return cls(
            name=name,
            transport=transport,
            command=command,
            env=env,
            url=url,
            headers=headers,
            endpoint=endpoint,
            tls=tls,
            timeout_seconds=timeout_seconds,
            enabled=enabled,
            cwd=cwd,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        d = {
            "name": self.name,
            "transport": self.transport.value,
            "command": list(self.command),
            "env": dict(self.env),
            "url": self.url,
            "headers": dict(self.headers),
            "endpoint": self.endpoint,
            "tls": self.tls,
            "timeout_seconds": self.timeout_seconds,
            "enabled": self.enabled,
        }
        if self.cwd is not None:
            d["cwd"] = self.cwd
        return d

    def validate(self) -> list[str]:
        """Validate the configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.name:
            errors.append("name is required")

        if self.transport == TransportType.STDIO:
            if not self.command:
                errors.append("command is required for stdio transport")
        elif self.transport == TransportType.HTTP:
            if not self.url:
                errors.append("url is required for http transport")
        elif self.transport == TransportType.GRPC:
            if not self.endpoint:
                errors.append("endpoint is required for grpc transport")

        return errors


@dataclass
class MCPConfigFile:
    """Represents a parsed MCP configuration file.

    A single file can contain one or multiple server definitions.

    Attributes:
        source_path: Path to the source file.
        servers: List of server configurations.
    """

    source_path: str
    servers: list[MCPServerConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: str = "") -> MCPConfigFile:
        """Parse configuration from dictionary.

        Supports two formats:
        1. Single server: {"name": "...", "transport": "...", ...}
        2. Multiple servers: {"servers": [{"name": "...", ...}, ...]}

        Args:
            data: Parsed JSON/YAML content.
            source_path: Path to the source file.

        Returns:
            MCPConfigFile instance.
        """
        servers: list[MCPServerConfig] = []

        # Check if it's a multi-server format
        if "servers" in data and isinstance(data["servers"], list):
            for server_data in data["servers"]:
                if isinstance(server_data, dict):
                    servers.append(MCPServerConfig.from_dict(server_data, source_path=source_path))
        # Otherwise treat as single server definition
        elif "name" in data:
            servers.append(MCPServerConfig.from_dict(data, source_path=source_path))

        return cls(source_path=source_path, servers=servers)


__all__ = [
    "MCPConfigFile",
    "MCPServerConfig",
    "TransportType",
]
