"""Tool domain execution-control exceptions."""

class PauseRequested(RuntimeError):
    """Raised when a pause is requested."""


class CancelRequested(RuntimeError):
    """Raised when cancellation is requested."""


class HumanApprovalRequired(RuntimeError):
    """Raised when HITL approval is required."""


__all__ = ["PauseRequested", "CancelRequested", "HumanApprovalRequired"]
