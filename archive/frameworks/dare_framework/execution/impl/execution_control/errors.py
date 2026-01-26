"""Kernel execution control errors (v2)."""


class PauseRequested(RuntimeError):
    """Raised by poll_or_raise when the control plane requests a pause."""


class CancelRequested(RuntimeError):
    """Raised by poll_or_raise when the control plane requests cancellation."""


class HumanApprovalRequired(RuntimeError):
    """Raised by poll_or_raise when HITL approval is required."""

