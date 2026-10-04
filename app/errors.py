class GatewayError(Exception):
    """Base class for all gateway errors."""


class RetryableError(GatewayError):
    """Temporary or provider-side problem: retry / fall back.
    Examples: 429, 5xx, timeout, connection error."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after  


class NonRetryableError(GatewayError):
    """The request or our config is the problem: stop, don't fall back.
    Examples: 400, 401, 403."""