"""Stdio transport for MCP communication.

The stdio transport launches an MCP server as a subprocess and communicates
via stdin/stdout using newline-delimited JSON-RPC messages.

This is the most common transport for local MCP servers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class StdioTransport:
    """MCP transport using subprocess stdin/stdout.

    Messages are sent as newline-delimited JSON. Each message must be
    a complete JSON object on a single line (no embedded newlines).

    The subprocess is started on connect() and terminated on close().
    Stderr is captured for logging but not parsed as MCP messages.

    Example:
        transport = StdioTransport(
            command=["mcp-server-fs", "--path", "/data"],
            env={"DEBUG": "1"},
        )
        await transport.connect()
        await transport.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        response = await transport.receive()
        await transport.close()
    """

    def __init__(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        cwd: str | None = None,
    ) -> None:
        """Initialize stdio transport.

        Args:
            command: Command and arguments to launch the MCP server.
            env: Additional environment variables for the subprocess.
                 These are merged with the current environment.
            timeout_seconds: Timeout for operations in seconds.
            cwd: Working directory for the subprocess (default: inherit).
        """
        if not command:
            raise ValueError("command cannot be empty")

        self._command = list(command)
        self._env = dict(env) if env else {}
        self._timeout = timeout_seconds
        self._cwd = cwd

        self._process: asyncio.subprocess.Process | None = None
        self._connected = False

        # Buffer for partial reads
        self._read_buffer = ""

    @property
    def is_connected(self) -> bool:
        """Check if connected to the subprocess."""
        return self._connected and self._process is not None

    async def connect(self) -> None:
        """Launch the MCP server subprocess.

        Raises:
            ConnectionError: If subprocess fails to start.
            FileNotFoundError: If command not found.
        """
        if self._connected:
            return

        # Merge environment
        env = os.environ.copy()
        env.update(self._env)

        try:
            logger.debug(f"Starting MCP server: {' '.join(self._command)}")
            kwargs: dict[str, Any] = {
                "stdin": asyncio.subprocess.PIPE,
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.PIPE,
                "env": env,
            }
            if self._cwd:
                kwargs["cwd"] = self._cwd
            self._process = await asyncio.create_subprocess_exec(
                *self._command,
                **kwargs,
            )
            self._connected = True
            logger.info(f"MCP server started (pid={self._process.pid}): {self._command[0]}")

            # Start stderr reader task for logging
            asyncio.create_task(self._read_stderr())

        except FileNotFoundError as e:
            raise ConnectionError(f"MCP server command not found: {self._command[0]}") from e
        except Exception as e:
            raise ConnectionError(f"Failed to start MCP server: {e}") from e

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message to the server via stdin.

        Args:
            message: JSON-RPC message to send.

        Raises:
            ConnectionError: If not connected or process terminated.
            IOError: If write fails.
        """
        if not self._connected or self._process is None:
            raise ConnectionError("Not connected to MCP server")

        if self._process.stdin is None:
            raise ConnectionError("stdin not available")

        # Check if process is still running
        if self._process.returncode is not None:
            raise ConnectionError(
                f"MCP server process terminated with code {self._process.returncode}"
            )

        try:
            # Serialize to JSON and add newline delimiter
            data = json.dumps(message, separators=(",", ":")) + "\n"
            self._process.stdin.write(data.encode("utf-8"))
            await self._process.stdin.drain()
            logger.debug(f"Sent: {message.get('method', message.get('id', '?'))}")
        except Exception as e:
            raise IOError(f"Failed to send message: {e}") from e

    async def receive(self) -> dict[str, Any]:
        """Receive the next JSON-RPC message from stdout.

        Returns:
            Parsed JSON-RPC message.

        Raises:
            ConnectionError: If not connected or process terminated.
            TimeoutError: If receive times out.
            IOError: If read fails.
        """
        if not self._connected or self._process is None:
            raise ConnectionError("Not connected to MCP server")

        if self._process.stdout is None:
            raise ConnectionError("stdout not available")

        try:
            # Read until we have a complete line
            while "\n" not in self._read_buffer:
                # Check if process terminated
                if self._process.returncode is not None:
                    raise ConnectionError(
                        f"MCP server process terminated with code {self._process.returncode}"
                    )

                # Read with timeout
                try:
                    chunk = await asyncio.wait_for(
                        self._process.stdout.read(4096),
                        timeout=self._timeout,
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Receive timeout after {self._timeout}s")

                if not chunk:
                    # EOF - process closed stdout
                    raise ConnectionError("MCP server closed connection")

                self._read_buffer += chunk.decode("utf-8")

            # Extract complete line
            line, self._read_buffer = self._read_buffer.split("\n", 1)
            line = line.strip()

            if not line:
                # Empty line, try again
                return await self.receive()

            # Parse JSON
            message = json.loads(line)
            logger.debug(f"Received: {message.get('method', message.get('id', '?'))}")
            return message

        except json.JSONDecodeError as e:
            raise IOError(f"Invalid JSON from MCP server: {e}") from e
        except asyncio.TimeoutError:
            raise
        except ConnectionError:
            raise
        except Exception as e:
            raise IOError(f"Failed to receive message: {e}") from e

    async def close(self) -> None:
        """Terminate the subprocess and cleanup.

        This method is idempotent - safe to call multiple times.
        """
        if not self._connected:
            return

        self._connected = False

        if self._process is not None:
            try:
                # Close stdin to signal EOF
                if self._process.stdin:
                    self._process.stdin.close()
                    await self._process.stdin.wait_closed()

                # Give process time to exit gracefully
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                    logger.debug(f"MCP server exited with code {self._process.returncode}")
                except asyncio.TimeoutError:
                    # Force terminate
                    logger.warning("MCP server did not exit gracefully, terminating")
                    self._process.terminate()
                    try:
                        await asyncio.wait_for(self._process.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        logger.warning("MCP server did not terminate, killing")
                        self._process.kill()
                        await self._process.wait()

            except Exception as e:
                logger.warning(f"Error closing MCP server: {e}")
            finally:
                self._process = None

        logger.info("MCP server connection closed")

    async def _read_stderr(self) -> None:
        """Background task to read and log stderr output."""
        if self._process is None or self._process.stderr is None:
            return

        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    logger.debug(f"[MCP stderr] {text}")
        except Exception as e:
            logger.debug(f"Stderr reader stopped: {e}")


__all__ = ["StdioTransport"]
