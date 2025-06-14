class ConnectorError(Exception):
    """Base exception for connector errors."""


class ConnectorNotInitializedError(ConnectorError):
    """Raised when the connector is not properly initialized."""


class DocumentProcessingError(ConnectorError):
    """Raised when there is an error processing a document."""


class HTTPRequestError(ConnectorError):
    """Raised when there is an error with HTTP requests."""

    def __init__(
        self, url: str, status_code: int | None = None, message: str | None = None
    ):
        self.url = url
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP request failed for {url}: {message or 'Unknown error'}")
