class ToolError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class ToolNotFoundError(Exception):
    pass


class ToolAccessDenied(Exception):
    pass


class ApprovalRequired(Exception):
    pass
