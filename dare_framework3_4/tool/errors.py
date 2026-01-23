"""Tool error definitions."""

from __future__ import annotations


class ToolError(RuntimeError):
    """Structured tool error with stable code and message."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


__all__ = ["ToolError"]
