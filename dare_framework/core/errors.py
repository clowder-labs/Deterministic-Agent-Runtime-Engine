class RuntimeErrorBase(Exception):
    """Base error for runtime failures."""


class StateError(RuntimeErrorBase):
    """Invalid runtime state transition."""


class PlanGenerationFailedError(RuntimeErrorBase):
    """Raised when plan loop cannot produce a valid plan within budget."""


class PolicyDeniedError(RuntimeErrorBase):
    """Raised when a policy enforcement blocks an action."""


class ToolExecutionError(RuntimeErrorBase):
    """Raised when a tool or work unit fails to reach completion."""


class UserInterruptedError(RuntimeErrorBase):
    """Raised when a user interrupts tool execution."""

    def __init__(self, message: str, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message
