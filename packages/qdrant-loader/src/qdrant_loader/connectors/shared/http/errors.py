class HTTPRequestError(Exception):
    """Generic HTTP request error for connectors.

    This exception can be raised by connectors to provide a common error type
    across different HTTP clients and retry strategies.
    """

    def __init__(self, url: str, message: str, status: int | None = None):
        super().__init__(message)
        self.url = url
        self.status = status
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - trivial
        status_part = f" status={self.status}" if self.status is not None else ""
        return f"HTTPRequestError(url={self.url}{status_part}): {self.message}"
