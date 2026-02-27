"""Security-domain error contracts."""

from __future__ import annotations


SECURITY_TRUST_DERIVATION_FAILED = "SECURITY_TRUST_DERIVATION_FAILED"
SECURITY_POLICY_CHECK_FAILED = "SECURITY_POLICY_CHECK_FAILED"
SECURITY_POLICY_DENIED = "SECURITY_POLICY_DENIED"
SECURITY_APPROVAL_MANAGER_MISSING = "SECURITY_APPROVAL_MANAGER_MISSING"


class SecurityBoundaryError(RuntimeError):
    """Structured error raised by security boundaries."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.reason = reason


__all__ = [
    "SECURITY_APPROVAL_MANAGER_MISSING",
    "SECURITY_POLICY_CHECK_FAILED",
    "SECURITY_POLICY_DENIED",
    "SECURITY_TRUST_DERIVATION_FAILED",
    "SecurityBoundaryError",
]
