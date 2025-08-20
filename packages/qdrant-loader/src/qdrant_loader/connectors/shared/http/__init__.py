"""Shared HTTP utilities for connectors.

Prefer importing from this package instead of legacy
`qdrant_loader.connectors.http`.
"""

from .client import (
    make_request_async,
    make_request_with_retries_async,
    aiohttp_request_with_retries,
)
from .errors import HTTPRequestError

__all__ = [
    "make_request_async",
    "make_request_with_retries_async",
    "aiohttp_request_with_retries",
    "HTTPRequestError",
]


