"""Exception types used by capability implementations (v2)."""


class ToolError(Exception):
    """Tool-raised error that can be converted into a failed ToolResult."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class ToolNotFoundError(Exception):
    """Raised when a tool capability cannot be resolved."""


class ToolAccessDenied(Exception):
    """Raised when policy denies access to a capability."""


class ApprovalRequired(Exception):
    """Raised when an action requires HITL approval (legacy-style tooling)."""

