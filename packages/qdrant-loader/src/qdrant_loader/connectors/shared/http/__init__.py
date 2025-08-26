"""Shared HTTP utilities for connectors.

Prefer importing from this package instead of legacy
`qdrant_loader.connectors.http`.
"""

from .client import (
    aiohttp_request_with_retries,
    make_request_async,
    make_request_with_retries_async,
)
from .errors import HTTPRequestError
from .policy import (
    aiohttp_request_with_policy,
    request_with_policy,
)
from .rate_limit import RateLimiter

__all__ = [
    "make_request_async",
    "make_request_with_retries_async",
    "aiohttp_request_with_retries",
    "HTTPRequestError",
    "RateLimiter",
    "request_with_policy",
    "aiohttp_request_with_policy",
]
